import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { generateMnemonic, mnemonicToSeedSync, validateMnemonic } from "@scure/bip39";
import { wordlist } from "@scure/bip39/wordlists/english.js";
import { HDKey } from "@scure/bip32";
import { keccak_256 } from "@noble/hashes/sha3.js";
import { hmac } from "@noble/hashes/hmac.js";
import { ripemd160 } from "@noble/hashes/legacy.js";
import { sha256, sha512 } from "@noble/hashes/sha2.js";
import { secp256k1 } from "@noble/curves/secp256k1.js";
import { ed25519 } from "@noble/curves/ed25519.js";
import { base58, base58check, bech32 } from "@scure/base";

const EVM_CHAINS = ["ethereum", "bsc", "polygon", "arbitrum", "base"];
const tron58 = base58check(sha256);

export function normalizeMnemonic(value) {
  return value.normalize("NFKD").toLowerCase().trim().split(/\s+/).join(" ");
}

function bytesToHex(bytes) {
  return [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function eip55(addressHex) {
  const lower = addressHex.toLowerCase().replace(/^0x/, "");
  const hash = keccak_256(new TextEncoder().encode(lower));
  let out = "";
  for (let i = 0; i < lower.length; i++) {
    const nibble = (hash[i >> 1] >> ((i & 1) === 0 ? 4 : 0)) & 0xf;
    const char = lower[i];
    out += nibble >= 8 ? char.toUpperCase() : char;
  }
  return `0x${out}`;
}

function secpChild(seed, path) {
  const node = HDKey.fromMasterSeed(seed).derive(path);
  if (!node.privateKey) throw new Error("派生失败");
  return node.privateKey;
}

function evmAddress(privateKey) {
  const uncompressed = secp256k1.getPublicKey(privateKey, false).slice(1);
  return eip55(bytesToHex(keccak_256(uncompressed).slice(-20)));
}

function bitcoinAddress(privateKey) {
  const compressed = secp256k1.getPublicKey(privateKey, true);
  const program = ripemd160(sha256(compressed));
  return bech32.encode("bc", [0, ...bech32.toWords(program)]);
}

function tronAddress(privateKey) {
  const uncompressed = secp256k1.getPublicKey(privateKey, false).slice(1);
  const payload = new Uint8Array(21);
  payload[0] = 0x41;
  payload.set(keccak_256(uncompressed).slice(-20), 1);
  return tron58.encode(payload);
}

export function slip10Master(seed) {
  const I = hmac(sha512, new TextEncoder().encode("ed25519 seed"), seed);
  return { key: I.slice(0, 32), chain: I.slice(32) };
}

function slip10Child(parent, index) {
  if (!Number.isSafeInteger(index) || index < 0x80000000) throw new Error("派生失败");
  const data = new Uint8Array(37);
  data[0] = 0x00;
  data.set(parent.key, 1);
  data[33] = (index >>> 24) & 0xff;
  data[34] = (index >>> 16) & 0xff;
  data[35] = (index >>> 8) & 0xff;
  data[36] = index & 0xff;
  const I = hmac(sha512, parent.chain, data);
  return { key: I.slice(0, 32), chain: I.slice(32) };
}

export function solanaPrivateKey(seed, accountIndex) {
  let node = slip10Master(seed);
  for (const index of [44, 501, accountIndex, 0]) node = slip10Child(node, index + 0x80000000);
  return node.key;
}

function solanaAddress(seed, accountIndex) {
  return base58.encode(ed25519.getPublicKey(solanaPrivateKey(seed, accountIndex)));
}

export function deriveAccounts(mnemonic, indices) {
  const seed = mnemonicToSeedSync(mnemonic);
  return indices.map((index) => {
    const evmPath = `m/44'/60'/0'/0/${index}`;
    const evm = evmAddress(secpChild(seed, evmPath));
    const bitcoinPath = `m/84'/0'/0'/0/${index}`;
    const tronPath = `m/44'/195'/0'/0/${index}`;
    const solanaPath = `m/44'/501'/${index}'/0'`;
    const addresses = [
      ...EVM_CHAINS.map((chain) => ({ chain, path: evmPath, address: evm })),
      { chain: "bitcoin", path: bitcoinPath, address: bitcoinAddress(secpChild(seed, bitcoinPath)) },
      { chain: "tron", path: tronPath, address: tronAddress(secpChild(seed, tronPath)) },
      { chain: "solana", path: solanaPath, address: solanaAddress(seed, index) },
    ];
    return { index, addresses };
  });
}

function reject(message) {
  throw new Error(message);
}

function checkedMnemonic(value) {
  if (typeof value !== "string" || value.length > 500) reject("助记词不正确");
  const mnemonic = normalizeMnemonic(value);
  const count = mnemonic === "" ? 0 : mnemonic.split(" ").length;
  if (count !== 12 && count !== 24) reject("只接受 12 或 24 个单词");
  if (!validateMnemonic(mnemonic, wordlist)) reject("助记词不正确");
  return { mnemonic, wordCount: count };
}

function checkedIndices(value) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 20) reject("请求无效");
  return value.map((item) => {
    if (!Number.isSafeInteger(item) || item < 0 || item > 1000) reject("请求无效");
    return item;
  });
}

export function run(input) {
  const indices = checkedIndices(input.indices);
  if (input.generate === true) {
    const mnemonic = generateMnemonic(wordlist, 128);
    return { mnemonic, word_count: 12, accounts: deriveAccounts(mnemonic, indices) };
  }
  const { mnemonic, wordCount } = checkedMnemonic(input.mnemonic);
  return { word_count: wordCount, accounts: deriveAccounts(mnemonic, indices) };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  let input;
  try {
    input = JSON.parse(readFileSync(0, "utf8"));
    if (!input || typeof input !== "object") throw new Error("请求无效");
    process.stdout.write(JSON.stringify(run(input)));
  } catch (error) {
    const message = error instanceof Error ? error.message : "请求无效";
    const allowed = new Set(["助记词不正确", "只接受 12 或 24 个单词", "请求无效"]);
    process.stdout.write(JSON.stringify({ error: allowed.has(message) ? message : "请求无效" }));
    process.exit(1);
  }
}
