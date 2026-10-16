# Web3 钱包（web3-wallet）

状态：待评审。本文只描述设计，不包含实现。

调查记录在 [docs/web3/metamask.md](../../web3/metamask.md) 和 [docs/web3/libraries.md](../../web3/libraries.md)。库的取舍以那两份记录为准。

## 1. 背景

资金账户里的「钱包实例」现在是空页面。要在这里创建或导入一套助记词，加密后放进 PostgreSQL，并列出这套助记词在各链上的收款地址。用户也可以为某一条链手工补一个收款地址。

MetaMask 的做法是：一套助记词进密码加密的保险库，账户按 BIP44 序号派生，EVM 各链共用一个地址。它没有提供能在服务器上创建并保管助记词的开发接口。本方案按同样的标准自己派生地址，不嵌入 MetaMask。

## 2. 目标

- 创建钱包：生成 12 个英文单词，页面只展示这一次。
- 导入钱包：用户输入助记词，通过 BIP39 校验后保存。
- 助记词以用户登录密码派生的密钥做 AES-256-GCM 后入库。
- 打开钱包看到各链收款地址。EVM 链地址相同。
- 可以按下一个序号再派生一个账户。
- 可以手工添加某条链的收款地址。只存地址。

## 3. 非目标

- 不签名、不转账、不查余额、不连接交易所。
- 不保存私钥，不提供「导出私钥」。
- 不接入 MetaMask 扩展、SDK 或 Snaps。
- 第一版 BIP39 口令固定为空，和 MetaMask HD keyring 一致。用户在别的钱包里如果设过额外口令，这里派生出的地址不会和那边相同。
- 不把助记词加密交给现有的 Fernet 主密钥。那把密钥和数据库在同一台控制机上，卷和库一起泄露就能解开全部助记词。SSH 密钥和卡号仍用 Fernet。

## 4. 引用的库

地址派生是一个单独的 Node 程序，运行时只依赖这五个精确版本：

| 包 | 版本 | 用途 |
| --- | --- | --- |
| `@scure/bip39` | 2.4.0 | 生成、校验、助记词转种子 |
| `@scure/bip32` | 2.4.0 | EVM、Bitcoin、Tron 的 secp256k1 派生 |
| `@noble/hashes` | 2.4.0 | Keccak-256、HASH160、HMAC-SHA512 |
| `@noble/curves` | 2.4.0 | Solana 的 ed25519 公钥 |
| `@scure/base` | 2.4.0 | Base58、Base58Check、Bech32 |

选择理由、审计时间和被排除的库见 [docs/web3/libraries.md](../../web3/libraries.md)。

助记词加密在 `web-api`：

| 库 | 用途 |
| --- | --- |
| `argon2-cffi` | 从登录密码派生 32 字节保险库密钥，算法 Argon2id |
| `cryptography` | AES-256-GCM。`ops` 已依赖此库 |

派生程序不依赖任何 `@metamask/*` 包。

## 5. 数据结构

三张新表。迁移用 Alembic。

### 5.1 `wallets`

| 字段 | 说明 |
| --- | --- |
| `id` | UUID |
| `name` | 展示名称，最长 80 |
| `ciphertext` | 版本化的密文 JSON，见第 6 节 |
| `mnemonic_sha256` | 规范化助记词的 SHA-256，十六进制。用来拒绝重复导入。128 位熵不能从这个哈希反推 |
| `word_count` | 12 或 24 |
| `created_at` | 时间 |

列表和详情接口不返回 `ciphertext` 和 `mnemonic_sha256`。

### 5.2 `wallet_accounts`

| 字段 | 说明 |
| --- | --- |
| `id` | UUID |
| `wallet_id` | 外键，删除钱包时级联删除 |
| `name` | 默认 `Account 1` 这种序号名，用户可改 |
| `derivation_index` | 从 0 递增。同一钱包内唯一。删除账户后不复用 |
| `created_at` | 时间 |

### 5.3 `wallet_addresses`

| 字段 | 说明 |
| --- | --- |
| `id` | UUID |
| `wallet_id` | 外键 |
| `account_id` | 派生地址指向 `wallet_accounts`。手工地址为空 |
| `chain` | 第 7 节的链标识 |
| `address` | 收款地址文本 |
| `derivation_path` | 派生地址写入完整路径。手工地址为空 |
| `source` | `derived` 或 `manual` |
| `label` | 可空备注，最长 80 |
| `created_at` | 时间 |

唯一约束：`(wallet_id, chain, address)`。

## 6. 加密

创建、导入、添加账户、查看助记词都要再提交当前登录密码。先用现有的 bcrypt 校验密码。校验失败就停止，不派生密钥。

通过后用 Argon2id 从这同一个密码派生保险库密钥。参数按 OWASP 对 Argon2id 的建议起步：内存 64 MiB，迭代 3，并行度 1。盐是每个钱包 16 字节随机数。参数和盐写进密文 JSON，以后加重参数时，旧钱包仍按自己的参数解密。JSON 里的 `m` 单位是 KiB，65536 即 64 MiB。

密文 JSON：

```json
{
  "v": 1,
  "kdf": "argon2id",
  "m": 65536,
  "t": 3,
  "p": 1,
  "salt": "<base64>",
  "nonce": "<base64，12 字节>",
  "ct": "<base64，AES-256-GCM 密文和标签>"
}
```

明文是 UTF-8 的助记词，单词之间一个空格。nonce 每次加密重新生成。密钥、密码、助记词不写入日志，不放进 session cookie，不发给 `ops`。

修改登录密码时，用旧密码解开全部钱包，再用新密码加密。有任何一条解不开，整次修改中止。

## 7. 地址

规范化：Unicode NFKD，小写，把连续空白收成一个空格，去掉首尾空白。然后做 BIP39 英文词表校验。生成只用 12 词。导入接受 12 或 24 词。

BIP39 口令为空字符串。

| 链标识 | 展示名 | 路径 | 地址 |
| --- | --- | --- | --- |
| `ethereum` | Ethereum | `m/44'/60'/0'/0/{n}` | Keccak-256 后 20 字节，EIP-55 |
| `bsc` | BNB Chain | 与 Ethereum 相同 | 与 Ethereum 相同 |
| `polygon` | Polygon | 与 Ethereum 相同 | 与 Ethereum 相同 |
| `arbitrum` | Arbitrum | 与 Ethereum 相同 | 与 Ethereum 相同 |
| `base` | Base | 与 Ethereum 相同 | 与 Ethereum 相同 |
| `bitcoin` | Bitcoin | `m/84'/0'/0'/0/{n}` | 压缩公钥的 P2WPKH，Bech32，前缀 `bc` |
| `tron` | Tron | `m/44'/195'/0'/0/{n}` | `0x41` 加以太坊 20 字节，再 Base58Check |
| `solana` | Solana | `m/44'/501'/{n}'/0'` | SLIP-0010 ed25519 公钥的 Base58 |

`{n}` 是 `derivation_index`。EVM 五条链各存一行，地址字符串相同。这是同一把公钥，不是五次独立派生。

Solana 路径全部是硬化索引，因为 ed25519 的 SLIP-0010 不能做普通派生。序号增加的是第三段 `501'/{n}'`，和 Phantom、Solflare 的账户模型一致。

手工地址只做格式校验：EVM 是 20 字节十六进制，Bitcoin 校验 Bech32，Tron 校验 Base58Check 且前缀为 `0x41`，Solana 是 32 字节 Base58。校验失败不入库。手工地址的 `source` 为 `manual`，页面上和派生地址分开标。

派生程序从标准输入读 JSON，往标准输出写地址。助记词不出现在命令行参数里。进程超时后结束。标准错误不回传助记词。`web-api` 拿到地址后立刻加密助记词，然后丢掉明文。

输入：

```json
{
  "mnemonic": "word word word ...",
  "indices": [0]
}
```

输出只含链、路径和地址，不含种子或私钥。

`web-api` 镜像在构建阶段用官方 Node 镜像执行 `npm ci`，运行阶段只保留 Node 可执行文件和这个程序。锁文件来自 `registry.npmjs.org`。

## 8. 接口和页面

前缀 `/api/wallets`，都要登录态。写助记词的接口还要校验登录密码。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/wallets` | 名称和创建时间 |
| `POST` | `/api/wallets` | 创建或导入。创建的响应带这一次的助记词。导入的响应不带 |
| `GET` | `/api/wallets/{id}` | 账户、各链地址、来源。没有助记词 |
| `POST` | `/api/wallets/{id}/accounts` | 提交密码，派生下一个序号 |
| `POST` | `/api/wallets/{id}/addresses` | 手工添加收款地址 |
| `POST` | `/api/wallets/{id}/mnemonic` | 提交密码，返回助记词 |
| `DELETE` | `/api/wallets/{id}` | 删除钱包及其地址 |

创建响应的助记词只出现在这一次 HTTP 响应里。页面要求用户确认已经抄写，确认之后不再从接口读取，除非用户主动查看。查看接口和现在查看完整卡号一样，是单独的动作。

页面仍放在 `/accounts/crypto`。列表上是「创建钱包」和「导入钱包」。详情按账户分组，账户下是各链地址，另外有「添加账户」和「添加收款地址」。

## 9. 测试向量

派生结果要和这些公开向量一致，否则不能合并：

- BIP39 英语向量：助记词、种子。
- MetaMask `hd-keyring.test.ts` 的向量。助记词 `finish oppose decorate face calm tragic certain desk hour urge dinosaur mango`，序号 0 的地址是 `0x1c96099350f13d558464ec79b9be4445aa0ef579`，序号 1 是 `0x1b00aed43a693f3a957f9feb5cc08afa031e37a0`。
- SLIP-0010 ed25519 的官方测试向量。
- BIP173 的 Bech32 向量，以及一条 BIP84 收款地址向量。
- 一条公开的 Tron 地址向量：同一私钥的以太坊地址和 Tron 地址必须对应。

加密测试覆盖错误密码、重复 nonce 不会发生、修改密码后仍能解开。日志夹具里不能出现助记词。
