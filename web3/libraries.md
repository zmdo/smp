# 钱包开发库调查

调查日期：2026-10-16。标准是：还在发版、有独立安全公司审计、依赖少、作者和发布渠道清楚、没有已知的投毒包。只做收款地址，不做转账，所以链上 RPC 客户端都不需要。

版本号以当天 npm 的 `latest` 为准。

## 采用

这五个包是同一个作者 Paul Miller 的 scure / noble 系列。MetaMask、ethers、viem 的底层曲线和哈希走到这一层。Noble 站点在 2026-08 统计，hashes 周下载约 6300 万，curves 约 2400 万。发布说明写明提交有 PGP 签名，npm 包走 GitHub 构建的 provenance。

| 包 | 锁定版本 | 最近发布 | 独立审计 | 本项目用它做什么 |
| --- | --- | --- | --- | --- |
| `@scure/bip39` | 2.4.0 | 2026-08-28 | Cure53，2022-01，针对 1.0.0。2026-04 作者对 2.2.0 做过自查 | 生成、校验助记词，助记词转 64 字节种子 |
| `@scure/bip32` | 2.4.0 | 2026-08-28 | Cure53，2022-01，针对 1.0.1。2026-04 作者对 2.2.0 做过自查 | secp256k1 的 BIP32。EVM、Bitcoin、Tron 都从这里派生 |
| `@noble/hashes` | 2.4.0 | 2026-08-27 | Cure53，2022-01，审计对象包含当时的 noble-hashes | SHA-256、RIPEMD-160、HMAC-SHA512、Keccak-256 |
| `@noble/curves` | 2.4.0 | 2026-08-27 | Trail of Bits，2026-08，针对 2.3.0。更早还有 Cure53（2024-09，ed25519 等）和 Kudelski（2023-09） | ed25519 公钥，给 Solana 地址用。secp256k1 的派生仍走 `@scure/bip32` |
| `@scure/base` | 2.4.0 | 2026-08-28 | 与 2022 年那次 Cure53 范围里的 base 编码同一系列 | Base58、Base58Check、Bech32 |

`@noble/curves@2.4.0` 的发布说明相对审计点 2.3.0 是加固：FROST 的轮次校验、Weierstrass 公钥边界、DER 长度限制、敏感参数快照。没有换曲线实现。可以锁 2.4.0。以后升级先读该版本的 “changes since audit”，再改锁定版本。

`@scure/bip32` 只支持 secp256k1。Solana 的 ed25519 不能用它做非硬化派生。SLIP-0010 规定 ed25519 只能硬化派生子密钥，主密钥是 `HMAC-SHA512("ed25519 seed", seed)`。这一步用已经审计的 `@noble/hashes` 的 HMAC，按 SLIP 原文实现，不另找一个 HD 包。测试必须对上 SLIP-0010 的官方向量。

Bitcoin 收款地址也不引入交易库。原生隔离见证（P2WPKH）是压缩公钥的 HASH160，再用 `@scure/base` 做 Bech32，人类可读部分是 `bc`。测试对 BIP173 和 BIP84 向量。

Tron 地址是同一条 secp256k1 公钥：非压缩公钥去掉前缀后做 Keccak-256，取后 20 字节，前面加 `0x41`，再 Base58Check。不需要 Tron 的 HTTP 客户端。

## 加密落库用的 Python 库

地址派生在 Node 里做，因为审计过的 BIP32 实现在上面这套 JS 库。助记词加密留在 `web-api`，用 Python：

| 库 | 理由 |
| --- | --- |
| `cryptography` | PyCA 维护。`ops` 已经依赖 `cryptography>=43.0.3`。用它的 AES-256-GCM，不自己拼 AES |
| `argon2-cffi` | 绑定官方 `libargon2`。Argon2id 是密码哈希竞赛的胜出算法，适合从登录密码派生保险库密钥 |

不使用 `browser-passworder`。它是给浏览器 WebCrypto 用的，KDF 是 PBKDF2。

## 不采用

| 库或接口 | 原因 |
| --- | --- |
| MetaMask 扩展、MetaMask SDK、Snaps Keyring API、`window.ethereum` | 这些是连接用户浏览器里的 MetaMask，或在 MetaMask 里写插件。读不到助记词，也不能在我们的数据库里建钱包。详见 [metamask.md](metamask.md) |
| `@metamask/eth-hd-keyring` | 浏览器 keyring。依赖 `@ethereumjs/tx`、`@metamask/eth-sig-util`、`@metamask/key-tree`、`@metamask/keyring-api` 等，远超过「算出地址」 |
| `@metamask/scure-bip39` | MetaMask 声明这是临时 fork，不长期维护，外部项目应使用 `@scure/bip39` |
| `ethereum-cryptography` | MetaMask 通过它调用 noble。我们直接依赖 noble 和 scure，少一层转出口 |
| `eth-account` 的 HD 接口 | 包本身由 ApeWorX 维护，0.14.0 发布于 2026-08-23，签名功能可用。助记词接口在文档里写明是未审计功能，必须先调用 `Account.enable_unaudited_hdwallet_features()`。不满足这次的审计要求 |
| PyPI 包 `web3-eth-account` | 仿冒 `eth-account` 的投毒包（OSV `MAL-2026-16129`）。安装脚本会拉取并执行远程代码。依赖名只能是 `eth-account`，本方案也不安装它 |
| `mnemonic`（Trezor `python-mnemonic`） | SatoshiLabs 的 BIP39 参考实现，信誉好，但只做到种子，不做多链地址。最新版 0.21 发布于 2024-01-05。没有 Cure53 这一档的库审计。日文词表往返在 2026 年仍有未合并修复。不作为本方案的派生实现 |
| `bip-utils`、`hdwallet` | 单维护者聚合库，依赖多，没有找到与 noble 同级的独立审计 |
| `bitcoinjs-lib` | 使用面广，但是完整的比特币交易库。收款地址用 `@scure/base` 即可 |
| `@scure/btc-signer` | 2023-02 有 Cure53 审计，作者也清楚。MuSig2 和 UTXO 选择未审计，还依赖 `micro-packed`。本方案不签名，不引入它 |
| `@solana/web3.js`、`@solana/kit`、`solders` | 链客户端，体积和依赖都大。地址只需要 ed25519 公钥的 Base58 |
| `tronpy`、`TronWeb` | 链客户端。地址算法用上面的 secp256k1 和 Base58Check 就能完成 |
| `ethers`、`viem` | 维护和审计都不错，但是完整的以太坊客户端。它们内部也是走到 scure / noble。直接依赖底层库，依赖更少 |

## 供应链约束

派生程序的 `package.json` 只允许上面五个运行时依赖，版本用精确号，不用 `^`。锁文件从 `https://registry.npmjs.org` 生成。现有 `apps/web-ui/package-lock.json` 指向联想内网源 `csnexus.lenovo.com.cn`，派生程序不能复用那份锁文件。

安装使用 `npm ci`。升级一个包之前，对照该包仓库里的审计记录和 “changes since audit”。
