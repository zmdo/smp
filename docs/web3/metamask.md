# MetaMask 实现调查

调查的是官方源码，不是浏览器商店里的打包扩展。扩展本身是界面和后台进程，钱包逻辑在它依赖的库里。

## 下载了什么

| 路径 | 包 | 版本 | 说明 |
| --- | --- | --- | --- |
| `tmp/metamask/accounts/packages/keyring-eth-hd` | `@metamask/eth-hd-keyring` | 15.0.1，npm 发布时间 2026-10-12 | 现行 HD 钱包。仓库是 [MetaMask/accounts](https://github.com/MetaMask/accounts) |
| `tmp/metamask/KeyringController` | `@metamask/eth-keyring-controller` | 17.0.1，npm 发布时间 2026-08-26 | 保险库：用密码加密全部 keyring，解锁后放进内存 |
| `tmp/metamask/browser-passworder` | `@metamask/browser-passworder` | 6.0.0 | 密码派生密钥并做 AES-GCM |
| `tmp/metamask/eth-hd-keyring` | 同名旧仓库 | 停在 7.0.1（2023-09） | 已经不是 npm 上的现行包。阅读时以 `accounts` 里的 15.0.1 为准 |

npm 上 `@metamask/eth-hd-keyring@15.0.1` 的 `repository.url` 是 `https://github.com/MetaMask/accounts.git`。

## 钱包怎么组成

MetaMask 把签名能力分成 keyring。现行控制器里两类内置 keyring 是：

| 类型字符串 | 作用 |
| --- | --- |
| `HD Key Tree` | 一套助记词派生出的以太坊账户 |
| `Simple Key Pair` | 单独导入的私钥，不从助记词推导 |

`KeyringType` 定义在 `tmp/metamask/KeyringController/src/constants.ts`。

一套助记词对应一个 HD keyring。再点「创建账户」时，控制器调用 `addNewAccount`，HD keyring 再派生下一个序号。导入私钥走 Simple Key Pair，能签名，不是只读地址。

## 助记词和派生

现行实现：`tmp/metamask/accounts/packages/keyring-eth-hd/src/hd-keyring.ts`。

- 生成：`generateMnemonic(wordlist)`，来自 `@metamask/scure-bip39`，默认 128 位熵，也就是 12 个英文单词。
- 校验：同一包的 `validateMnemonic`。校验失败不写入实例字段。
- 种子：`mnemonicToSeed(mnemonic, '')`。第二参数是 BIP39 口令，这里固定为空字符串。
- 路径：`m/44'/60'/0'/0`，再 `deriveChild(i)`。账户 1 是序号 0，账户 2 是序号 1。
- 地址：公钥经 `@ethereumjs/util` 的 `publicToAddress`，得到小写 `0x` 地址。
- 序列化进保险库的内容是助记词的 UTF-8 字节、账户数量、路径。它不逐个保存序号。

他们自己的测试向量（`src/hd-keyring.test.ts`）：

- 助记词：`finish oppose decorate face calm tragic certain desk hour urge dinosaur mango`
- 序号 0：`0x1c96099350f13d558464ec79b9be4445aa0ef579`
- 序号 1：`0x1b00aed43a693f3a957f9feb5cc08afa031e37a0`

这是公开测试向量，不是可用资金的助记词。

HD keyring 只做以太坊 secp256k1 路径。Bitcoin、Solana、Tron 不在这个类里。EVM 兼容链共用这一个地址，MetaMask 换网络时不换地址。

## 助记词怎么加密

`KeyringController.persistAllKeyrings` 把所有 keyring 序列化成一个数组，交给 `browser-passworder` 加密，密文放在本地保险库。解锁时 `submitPassword` 解密，keyring 只活在内存里。`setLocked` 删掉密码和内存中的 keyring。

`tmp/metamask/browser-passworder/src/index.ts` 的现行参数：

- KDF：PBKDF2，默认 900000 次迭代。旧保险库是 10000 次。
- 加密：WebCrypto AES-GCM。
- 盐和算法参数跟密文一起保存。

密码不进保险库。拿到磁盘上的保险库，没有密码就解不开助记词。

查看助记词是扩展内部界面，要先通过密码或保险库验证，再把助记词显示给用户。网页里的 `window.ethereum` 拿不到它。2019 年的扩展 issue [#7364](https://github.com/MetaMask/metamask-extension/issues/7364) 讨论过增加导出助记词的 provider 方法，没有变成公开接口。

## 有哪些开发接口

这些接口都存在，但没有一个是「把 MetaMask 嵌进我们的服务器、替我们生成并保管助记词」。

### 1. Keyring 类协议（扩展内部）

HD keyring 实现的是给 MetaMask 后台用的类，不是 HTTP API。网站不能调用。主要方法：

| 方法 | 作用 |
| --- | --- |
| `generateRandomMnemonic` | 生成助记词 |
| `deserialize` / `serialize` | 恢复和导出待加密状态 |
| `addAccounts` | 按序号继续派生 |
| `getAccounts` | 返回地址 |
| `exportAccount` | 导出某个地址的私钥 |
| `signTransaction` / `signPersonalMessage` / `signTypedData` | 签名 |

文档在旧仓库 README，现行类在 `accounts` 的 `hd-keyring.ts`。这是插件协议：别人可以写新的 keyring 放进 MetaMask，不是给我们的后端用的 SDK。

### 2. 注入的 provider

扩展向网页注入 EIP-1193 provider（`window.ethereum`），并用 EIP-6963 声明自己。Dapp 可以请求账户、请用户签名。用户拒绝就失败。这个接口不返回助记词，也不返回私钥。

### 3. MetaMask SDK

给手机端或没有扩展的环境，把 Dapp 连到用户自己的 MetaMask。方向和本项目相反：我们要在控制机上创建并保存钱包，不是去连接用户浏览器里已有的 MetaMask。

### 4. Snaps 与 Keyring API

[Keyring API](https://docs.metamask.io/snaps/reference/keyring-api/) 让账户管理 Snap 在 MetaMask 里面托管它自己的账户。官方说明这些 Snap 读不到用户现有的助记词。上架还要求 Snap 有独立审计。

`keyring_exportAccount` 可以由 Snap 自己决定是否导出私钥，只对 Snap 清单里允许的 Dapp 开放，而且 MetaMask 自己的源站不能调用它。这仍然是浏览器里的第三方插件，不是服务器上的钱包库。

### 5. `@metamask/scure-bip39`

现行 HD keyring 的助记词函数来自 MetaMask 对 `@scure/bip39` 的 fork。该 fork 的说明写明它是临时分支，不接受社区 issue，其他项目应直接使用 `@scure/bip39`。见 [MetaMask/scure-bip39](https://github.com/MetaMask/scure-bip39)。

## 对本项目有用的部分

采用这些做法：

- 一套助记词是一个钱包。账户按 BIP44 序号递增，从 0 开始。
- EVM 路径使用 `m/44'/60'/0'/0/{序号}`，空 BIP39 口令。
- 生成 12 个单词，导入时做 BIP39 校验。
- 助记词只以密码派生的密钥加密后落盘。解锁或查看时才解密，用完不留在响应之外的存储里。
- 列表只给地址，不给助记词。

不照搬这些部分：

- 不把 MetaMask 扩展、SDK 或 Snap 嵌进来。
- 不依赖 `@metamask/eth-hd-keyring`、`@metamask/scure-bip39`、`ethereum-cryptography`。前者是浏览器 keyring，依赖面包括签名、交易和 MetaMask 自己的工具包；fork 明确不建议外部使用。
- 不把「添加收款地址」做成 Simple Key Pair。那会保存私钥并能签名。本项目的手动地址只保存地址。
- 不把持久化状态做成「只记账户个数」。MetaMask 序列化的是 `numberOfAccounts`，删除中间账户后再恢复，序号可能重新从 0 排。我们的表保存每个账户的派生序号，删除后不复用。
- 密码学 KDF 不用浏览器里的 PBKDF2。控制机是 Python 服务，用 Argon2id。加密算法同样是 AES-GCM。
