# 深度登记 字幕交付校对册

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 字幕文件采信 | 核对逐行隔离与重复字幕 | `/sheet/source` `/api/check/source` | `app/modules/source/service.py` | `tests/test_source.py` |
| M2 帧率与丢帧约束 | 复查非法标签、精确换算与卷偏移 | `/sheet/clock` `/api/check/clock` | `app/modules/clock/timecode.py` `app/modules/clock/sync.py` | `tests/test_clock.py` `tests/test_sync.py` |
| M3 切版段映射 | 按切版重建目标帧 | `/` `/api/check/edits` | `app/modules/edits/contract.py` `app/modules/edits/mapping.py` | `tests/test_edits.py` |
| M4 字幕冲突定位 | 定位同轨重叠帧与原行组 | `/sheet/overlaps` `/api/check/overlaps` | `app/modules/overlaps/service.py` | `tests/test_overlaps.py` |
| M5 时长与丢段对账 | 查看并集覆盖守恒 | `/sheet/balance` `/api/check/balance` | `app/modules/balance/service.py` | `tests/test_balance.py` |
| M6 批次留档复跑 | 保存原件并逐值复算 | `/sheet/runs` `POST /api/runs` | `app/modules/runs/files.py` `app/modules/runs/service.py` | `tests/test_runs.py` |
| M7 交付证据签发 | 下载经散列核验的交付证据 | `/sheet/delivery` `/api/delivery/<key>/export` | `app/modules/delivery/checks.py` | `tests/test_delivery.py` `tests/test_sync.py` |

## 换带同步规则

| 规则 | 处理位置 | 测试 |
|---|---|---|
| 旧片换带重置时码，字幕按卷同步点锚到母带帧，禁止沿用前一卷偏移 | `app/modules/clock/sync.py` `app/modules/clock/service.py` | `tests/test_sync.py::test_same_timecode_lands_on_each_reels_master_frame` |
| 同一带位时码跨卷各自落在本卷母带画面 | `app/modules/clock/sync.py` `app/modules/edits/mapping.py` | `tests/test_sync.py::test_same_timecode_lands_on_each_reels_master_frame` |
| 同卷同步点算出不同偏移，整卷留待复核 | `app/modules/clock/sync.py` | `tests/test_sync.py::test_conflicting_offsets_hold_whole_reel` |
| 跨卷整句只对齐半边时整句暂扣，签发包不放半句 | `app/modules/edits/mapping.py` `app/modules/delivery/checks.py` | `tests/test_sync.py::test_cross_reel_half_aligned_withholds_full_sentence` |
| 切版未保留整卷画面时，缺同步点不记作待核 | `app/modules/clock/sync.py` | `tests/test_sync.py::test_reel_without_kept_picture_is_exempt_not_pending` |
| 签发包带用过的同步点，晚到记录补齐后重算新档 | `app/modules/delivery/service.py` `app/modules/runs/service.py` | `tests/test_sync.py::test_downloaded_package_carries_used_sync_points` |

## 陷阱登记

| TRAP | 现象 | 朴素实现 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | 脏字幕首列 BOM | 首列无效 | 去首 BOM | `app/modules/source/reader.py` | `tests/test_source.py::test_bom_and_alias` |
| TRAP-04 | 脏字幕重复表头 | 当成字幕计算 | 单列分段 | `app/modules/source/reader.py` | `tests/test_source.py::test_repeated_header` |
| TRAP-05 | C112 多余列 | 文本错位 | 保留整行隔离 | `app/modules/source/reader.py` | `tests/test_source.py::test_width_and_missing` |
| TRAP-07 | C110 时码 N/A | 当成零帧 | 隔离必填空值 | `app/modules/source/service.py` | `tests/test_source.py::test_width_and_missing` |
| TRAP-09 | 9007199254740993 | 浏览器数值吞位 | 字符串保形 | `app/modules/source/service.py` | `tests/test_source.py::test_string_identity` |
| TRAP-10 | C104 使用分数帧率 | 假设 30 或先舍入 | 保留端点有理数至最后 | `app/modules/clock/timecode.py` | `tests/test_clock.py::test_exact_rate` |
| TRAP-14 | C111 内容相撞 | 后稿静默覆盖 | 同号矛盾整组隔离 | `app/modules/source/service.py` | `tests/test_source.py::test_conflicting_revision` |
| TRAP-17 | `legacy_id` 旧表头 | 硬读当前字段失败 | 按列别名迁移 | `app/modules/source/service.py` | `tests/test_source.py::test_bom_and_alias` |
| TRAP-23 | C115 与 C116 首尾相接 | 共同边界算重叠 | 半开区间扫线 | `app/modules/overlaps/sweep.py` | `tests/test_overlaps.py::test_touch_is_not_overlap` |

## 守恒与范围

脏样例 1140 源帧 = 740 交付 + 200 移除 + 200 待证。65 个重叠目标帧独立记录，5 条隔离记录无法量化。原件为带格式列的供应商抽取 CSV，DF 参数固定为 29.97，目标固定 24 fps。

换带样例 `taped` 四卷：R1、R2 同步点一致（偏移 1800），同一带位时码 `FRAME 100` 分别锚到母带 1900；R3 两个同步点给出 2900/3000 两个偏移而整卷复核，跨 R2/R3 的 C303 两个 KEEP 半边共 60 源帧暂扣，仅 40 源帧可签发；R4 整卷 `REMOVE`，缺同步点按豁免不记待核。补齐统一偏移的晚到同步记录后重算，新归档可签发且同步点证据随包下载。
