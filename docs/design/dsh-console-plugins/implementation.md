# 控制台插件实施计划

状态：第四步已完成。本文只排实施顺序，不改 `design.md` 里已经定下的决策。

运行版本钉在 `0.2.1-alpha.5`。调查用的源码在 `tmp/deepseek-harness`（`1517a4db`），该目录不进仓库。正式启动用 npm 上的 `@deepseek-ai/dsh@0.2.1-alpha.5`，不改这份检出。

插件放在本仓库 `apps/console-plugins/`。每个插件是一个组合包：`package.json` 声明 `dsh.bundle` 和 `engines.dsh`，`cordis.patch.yml` 插入插件行。客户端界面另声明 `dsh.client`（`platform: web`），并导出 `./client`。浏览器入口导出 `apply(ctx)`。React 从 `dsh` 的模块表里 `require('react')`，不把第二份 React 打进包。

安装进 `web` profile，不发布到插件市场：

```sh
dsh plugin --profile web add file:/绝对路径/apps/console-plugins/<插件>
dsh --profile web
```

`web` profile 首次使用时自带 `dsh-base` 和 `dsh-web-app`。本仓库的插件追加在这两层之后。

## 1. 空壳

只做一个壳插件 `apps/console-plugins/shell`，包名 `@smp/console-shell`。

- 以优先级 `-100` 注册 `sidebar`。默认侧栏是 `0`，数值更小的被画出来。画出现有控制台的导航：概览（仪表盘、军师）、运营（量化交易 / 数字货币）、资源（资金账户、服务器）、底部的平台设置。
- 以键 `console` 注册 `main`。`conversation` 仍留给 `dsh` 的会话。壳在 `console` 上声明内容槽 `console.page`，按栏目 id 取页面。这一步没有栏目插件，槽是空的，壳自己画出空面板和顶部 Tab。
- 点「军师」时 `layout.selectPanel(null)`，中间回到会话。原侧栏被换掉后，会话列表不再出现，所以壳在「军师」下面留会话列表和新会话。点一条会话调用现有的 `uiWorkspace.openSession`。
- 样式只挂在壳的两个根上：侧栏 `.smp-shell`，内容区 `.smp-console`。内容区里继续用 `panel`、`panel-head`、`mark`。不改 `body`，不改 `--dsw-*`。
- 不迁页面，不加反向代理，也不停现有单页应用。

验收：打开 `dsh --profile web` 后，左侧是控制台导航，中间是空面板；点「军师」能回到会话，并能从壳里选一条会话。

## 2. 反向代理

入口仍同时提供现有单页应用和 `dsh`。这一步只把两条路接到同一台主机上。`dsh` 的页面按它自己的部署方式挂在前缀后面，代理去掉前缀再转给监听器。单页应用继续占用站点根和 `/api`，所以现有页面还能用。

对外只有 `8080`：

| 浏览器路径 | 转到 |
| --- | --- |
| `/` | 现有单页应用 |
| `/api/` | 网站后台。单页应用仍走这里 |
| `/console-api/` | 去掉该前缀后转到网站后台的 `/api`。终端是 `/console-api/servers/:id/terminal` |
| `/mcp` | 网站后台 |
| `/dsh/` | 去掉 `/dsh` 后转到 `dsh web` 的 `/`、`/api` 和 `api/remote.mux`。这一段的请求体上限是 32MB |

`dsh` 在组合网络里听 `3080`，不把这个端口公布到宿主机。代理保留浏览器的 `Host`，并把它的 cookie 路径改到 `/dsh/`。接受的主机名是 `127.0.0.1` 和 `localhost`。网站后台不加跨域。

## 3. 迁页面

插件里的请求走统一的读取函数：把原来的 `/api` 换成 `/console-api`，并带上 cookie。没有 `smp_session` 时，浏览器打开单独的 `/login`，不加载控制台侧栏。登录成功后宿主放行页面和军师连接，不再用 `dsh` 打印的启动 token 开门。

栏目插件只往 `console.page` 注册，不注册 `sidebar.panellist`。顺序：

1. 仪表盘
2. 平台设置（登录安全、MCP）
3. 资金账户（钱包实例、详情、虚拟信用卡）
4. 数字货币（概览、行情、交易所、交易策略）
5. 服务器（实例、登记、详情、密钥，最后是终端的 WebSocket）

面板继续用现在的结构和文案。样式只写在 `.smp-console` 下面。

谁在没有 `smp_session` 时画出登录，以及 `dsh` 占住地址之后书签落在哪一条路径，在这一步写进壳的行为，不提前改 `design.md` 的决策。

栏目按功能拆开，各自注册到壳声明的 `console.page`：仪表盘、数字货币、资金账户、服务器、平台设置。军师仍是壳里切回 `dsh` 会话的入口。这些插件在同一个 `dsh` 进程里，登录状态放在页面之间共用的一份存储上。网站后台和运维服务仍是单独的进程。仪表盘、数字货币概览、交易策略仍是原来的空文案。

## 4. 切换入口

网站镜像不再构建现有单页应用。控制机保留网站后台、运维服务、数据库，并加一个 `dsh web`。对外仍只暴露网站入口。`dsh` 继续在组合网络里听 `3080`，不把这个端口公布到宿主机。

浏览器打开的是站点根上的 `dsh`。`/api` 归 `dsh`。控制台接口仍走 `/console-api/`。

| 浏览器路径 | 转到 |
| --- | --- |
| `/`、`/api`、静态资源和 `api/remote.mux` | `dsh web`。这一段的请求体上限是 32MB |
| `/console-api/` | 去掉该前缀后转到网站后台的 `/api`。终端是 `/console-api/servers/:id/terminal` |
| `/mcp` | 网站后台 |
| `/dsh/` | 跳回站点根，地址带上浏览器原来的主机和端口 |

代理保留浏览器的 `Host`。`dsh` 的 cookie 路径是 `/`。接受的主机名是 `127.0.0.1` 和 `localhost`。网站后台不加跨域。单页应用的源码还在 `apps/web-ui`，网站镜像只复制入口配置，不再编译它。
