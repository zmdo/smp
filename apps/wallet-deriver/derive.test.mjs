import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { deriveAccounts, normalizeMnemonic, slip10Master } from "./derive.mjs";

const METAMASK = "finish oppose decorate face calm tragic certain desk hour urge dinosaur mango";

test("MetaMask 向量的 EVM 地址一致", () => {
  const [first, second] = deriveAccounts(METAMASK, [0, 1]);
  assert.equal(first.addresses.find((item) => item.chain === "ethereum").address.toLowerCase(), "0x1c96099350f13d558464ec79b9be4445aa0ef579");
  assert.equal(second.addresses.find((item) => item.chain === "ethereum").address.toLowerCase(), "0x1b00aed43a693f3a957f9feb5cc08afa031e37a0");
  const evm = first.addresses.filter((item) => ["ethereum", "bsc", "polygon", "arbitrum", "base"].includes(item.chain));
  assert.equal(new Set(evm.map((item) => item.address)).size, 1);
});

test("BIP84 收款地址", () => {
  const mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about";
  const [account] = deriveAccounts(mnemonic, [0]);
  assert.equal(account.addresses.find((item) => item.chain === "bitcoin").address, "bc1qcr8te4kr609gcawutmrza0j4xv80jy8z306fyu");
  assert.equal(
    account.addresses.find((item) => item.chain === "ethereum").address.toLowerCase(),
    "0x9858effd232b4033e47d90003d41ec34ecaeda94",
  );
});

test("SLIP-0010 ed25519 主密钥", () => {
  const seed = Uint8Array.from({ length: 16 }, (_, index) => index);
  const master = slip10Master(seed);
  assert.equal(
    [...master.key].map((byte) => byte.toString(16).padStart(2, "0")).join(""),
    "2b4be7f19ee27bbf30c667b642d5f4aa69fd169872f8fc3059c08ebae2eb19e7",
  );
});

test("助记词规范化折叠空白", () => {
  assert.equal(normalizeMnemonic("  Abandon   ABANDON "), "abandon abandon");
});

test("命令行不把助记词写到标准错误", () => {
  const child = spawnSync(process.execPath, ["derive.mjs"], {
    input: JSON.stringify({ mnemonic: "not a mnemonic", indices: [0] }),
    encoding: "utf8",
  });
  assert.notEqual(child.status, 0);
  assert.equal(child.stderr, "");
  assert.equal(JSON.parse(child.stdout).error, "只接受 12 或 24 个单词");
  assert.equal(child.stdout.includes("not a mnemonic"), false);
});
