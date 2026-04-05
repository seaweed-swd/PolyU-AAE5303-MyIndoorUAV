# IndoorUAV-Agent 项目阶段总结（2026-04-05）

## 1. 项目背景与目标

本次工作的核心目标，是在 `IndoorUAV-Agent` 项目基础上，完成一套**可持续运行、可分 episode 归档、可自动计算指标**的 VLN（Vision-Language Navigation）批量评测流程，并将结果稳定保存下来，便于后续分析、对比与复现实验。

当前工作并不是从零训练模型，而是围绕官方仓库提供的在线评测能力，结合本地环境与数据目录布局，完成以下几件事：

1. 跑通 `IndoorUAV-Agent` 的 VLN 在线评测链路；
2. 将评测改造成 **episode-by-episode** 的批处理模式；
3. 为每个 episode 单独保存视频、轨迹、动作记录和评价指标；
4. 将最终结果写入数据盘，避免结果目录继续占用系统盘；
5. 对已完成样本做阶段性统计，形成可直接阅读的结果总结文件。

---

## 2. 使用到的仓库与组件

本次项目涉及的核心仓库/组件主要有以下几部分。

### 2.1 主仓库：`IndoorUAV-Agent`

仓库路径：

- `/root/AAE5303/IndoorUAV-Agent`

这是本次工作的主入口。根据仓库 `README.md`，该项目对应论文：

- **IndoorUAV: Benchmarking Vision-Language UAV Navigation in Continuous Indoor Environments**

仓库本身提供了：

- 预训练的 `IndoorUAV-Agent` 模型使用方式；
- 在线评测脚本（VLA / VLN）；
- 指标评测脚本；
- 微调配置与说明；
- 与 `openpi`、`Habitat-Sim` 的联动方式。

### 2.2 `openpi`

仓库内包含 `openpi/` 目录，用于模型推理侧环境与配置。根据官方说明，模型推理环境与模拟器环境不兼容，因此需要分环境运行。

在这次工作里，`openpi` 不是我们重点修改的部分，但它是模型推理链路的基础依赖。

### 2.3 `Habitat-Sim`

用于室内连续导航仿真。VLN 在线评测时，仿真器负责：

- 加载场景；
- 接收控制指令；
- 输出相机图像；
- 更新 UAV 状态与轨迹。

### 2.4 IndoorUAV 数据集

根据官方说明，数据集来自 ModelScope。评测中实际依赖的数据包括：

- 场景数据；
- `without_screenshot` 数据；
- 各条轨迹及其 `posture.json`；
- instruction 清单。

在当前环境中，评测脚本会使用：

- `test_vln_unseen.json` 作为 unseen VLN 评测清单；
- `without_screenshot/.../posture.json` 作为 GT 轨迹来源；
- `shared_folder/` 作为运行过程中的中间交换目录。

---

## 3. 本次实现与使用的核心脚本

这次工作的主脚本是：

- `/root/AAE5303/IndoorUAV-Agent/run_vln_unseen_eval_v2.py`

它不是仓库默认入口，而是为这次批量评测单独使用的一版 episode 级执行脚本。它的核心职责如下：

1. 读取 unseen VLN manifest；
2. 按 episode 单条运行，而不是整批一次性压上去；
3. 每条 episode 启动一套评测服务：
   - `model_runner.py`
   - `sim_runnner.py`
   - `vln_controller.py`
4. 等待当前 episode 输出轨迹结果；
5. 杀掉相关进程并归档本条 episode 的产物；
6. 导出视频、动作轨迹和指标；
7. 将阶段结果持续写入 `summary.partial.json`；
8. 全部完成后再写 `summary.json` 和 `overall_metrics.json`。

该脚本内部还实现了几个非常关键的处理步骤：

- `ensure_empty_shared_folder(...)`：每条 episode 前清空中间共享目录；
- `wait_for_episode_result(...)`：轮询等待当前 episode 的轨迹输出；
- `export_video(...)`：把图像序列导出为 `episode.mp4`；
- `build_action_trace(...)`：从轨迹 json 提取动作/轨迹信息，生成 `interaction_actions.json`；
- `compute_vln_metrics(...)`：读取 GT 轨迹，计算 `NE / SR / OSR / nDTW` 等指标；
- `backup_shared_folder(...)`：把本条 episode 的 `shared_folder` 归档到结果目录中，便于复查。

---

## 4. 整个评测 pipeline

本次实际跑通的 pipeline 可以概括为：

### 阶段 A：准备 manifest

使用 unseen VLN 的 JSON 文件作为 episode 清单。脚本每次只抽取一条 episode，写入临时 manifest：

- `current_episode_manifest.json`

同时替换当前运行使用的：

- `test_vln_unseen.json`

这样做的好处是：

- 可以把整批大任务拆成单条 episode 执行；
- 每条 episode 的日志和产物可以独立保存；
- 某条出错不会直接污染整批结果；
- 后续恢复、定位问题、查看视频都更方便。

### 阶段 B：启动三个服务

每条 episode 依次启动：

1. `model_runner.py`：负责模型推理；
2. `sim_runnner.py`：负责仿真环境；
3. `vln_controller.py`：负责把指令、感知和控制连起来。

这三者通过 `shared_folder/` 协作，交换：

- 图像；
- 模型输入输出；
- controller 输入；
- trajectory 结果。

### 阶段 C：等待 episode 结束

脚本会持续轮询：

- `shared_folder/trajectories/{episode_name}.json`

只要这个轨迹文件出现，就认为该条 episode 已完成，可以进入归档阶段。

如果超时，则记为失败，并在结果目录中保留错误信息。

### 阶段 D：归档单条 episode 产物

每条 episode 完成后，脚本会在本次运行目录下建立独立子目录，例如：

- `episodes/0001__gibson_1_Brevort_traj_-1_instruction.json/`

其中会保存：

- `episode.mp4`：本条 episode 的可视化视频；
- `interaction_actions.json`：动作轨迹/交互轨迹；
- `metrics.json`：本条 episode 的量化指标；
- `shared_folder/`：本条 episode 运行时的完整中间目录备份。

### 阶段 E：写阶段汇总

每完成一条 episode，就把当前累计结果写入：

- `summary.partial.json`

这样即使大任务中断，也不会丢掉前面已完成的统计。

全部完成后，还会生成：

- `summary.json`
- `overall_metrics.json`

---

## 5. 环境与安装思路

根据项目 README，本项目需要两个相互独立的环境：

### 5.1 模拟器环境

用于运行 Habitat-Sim 相关内容。

在当前脚本中，对应环境名：

- `habitat`

主要服务：

- `sim_runnner.py`
- `vln_controller.py`

### 5.2 模型推理环境

用于运行 `openpi` 及 IndoorUAV-Agent 模型推理。

在当前脚本中，对应环境名：

- `base`

主要服务：

- `model_runner.py`

### 5.3 依赖配置方式

项目官方 README 中指出：

1. Habitat-Sim 环境需按官方仓库安装；
2. 模型环境应参考项目自带的 `openpi/README.md`；
3. 配置文件中还需要设置：
   - 数据集路径；
   - 模型 checkpoint 路径；
   - scene 数据路径；
   - `training_data` 元信息路径。

### 5.4 本次实际采用的运行方式

在本次环境中，我们没有重新设计官方整套启动方式，而是直接通过 `run_vln_unseen_eval_v2.py` 在脚本中显式调用：

- `source /root/miniconda3/etc/profile.d/conda.sh`
- `conda activate base`
- `conda activate habitat`

并由 Python 的 `subprocess.Popen` 在不同 episode 中反复拉起和关闭所需服务。

这种做法的优点是：

- 不依赖手工多终端协调；
- 易于批量运行；
- 每条 episode 的生命周期清晰；
- 更适合长期 unattended 评测。

---

## 6. 这次过程中遇到的主要问题

这次推进过程中，实际上遇到了几类比较典型的问题。

### 6.1 默认结果目录还在系统盘

最初脚本默认：

- `--result-dir = result`

这意味着结果会被写到仓库路径下，也就是系统盘。

后来已经将默认结果目录改到了数据盘：

- `/data1/liuy/IndoorUAV-Agent-result`

这样至少**最终归档结果**不再继续挤占系统盘空间。

### 6.2 参数定义误改导致 `--result-dir` 重复

在人工调整参数时，曾出现过：

- `--result-dir` 重复定义两次；
- `--manifest` 参数一度被覆盖或缺失。

这类问题会导致：

- 参数解析混乱；
- 后续代码读取 `args.manifest` 时可能报错。

最终已经修正为正确的参数顺序与定义：

- `--repo-root`
- `--result-dir`
- `--manifest`
- `--base-env`
- `--habitat-env`
- `--limit`
- `--start-index`
- `--fps`

### 6.3 系统盘爆满，但数据盘增长不明显

这是本次最关键的工程问题之一。

表面上看，结果已经写到 `/data1`，但系统盘依然快速被占满。分析后发现原因并不是 `result-dir` 没生效，而是：

1. **最终结果目录**确实写到了数据盘；
2. 但**运行过程中的工作目录**仍在系统盘，例如：
   - `/root/AAE5303/IndoorUAV-Agent/shared_folder`
   - `/tmp`
   - 以及历史残留的 `/root/autodl-tmp`

其中检查时看到：

- `/root/autodl-tmp` 体积非常大；
- `/tmp` 中存在大量 `pip-unpack-*` 临时目录；
- `shared_folder` 仍位于系统盘仓库目录下。

因此出现了一个非常典型的现象：

- **最终归档产物**在数据盘增长；
- **运行过程产生的中间数据和历史缓存**仍不断消耗系统盘。

这也是“系统盘先满、数据盘看起来没怎么涨”的根本原因。

### 6.4 需要确认每条 episode 是否都形成完整产物

为了确保这一版 pipeline 真正可用，还专门检查了单条 episode 目录结构，确认至少应包含：

- 视频；
- 动作轨迹；
- 预测轨迹；
- 评价指标。

最终确认当前已完成的样本中，这四类产物都已正常落盘。

---

## 7. 解决方式与最终稳定方案

针对上述问题，这次采用的解决方式主要有以下几项。

### 7.1 结果目录迁移到数据盘

把评测结果从仓库默认相对路径切换到：

- `/data1/liuy/IndoorUAV-Agent-result`

这样每条 episode 归档后的：

- 视频；
- `interaction_actions.json`；
- `metrics.json`；
- `shared_folder` 备份；
- 阶段汇总文件；

都统一放在数据盘，便于长期保存与后续分析。

### 7.2 使用单条 episode 顺序执行

相比一次性整批跑，当前 `v2` 方案采取按条执行的策略：

- 每条只启动当前所需服务；
- 跑完就归档、写汇总、再清空共享目录；
- 降低了批处理过程中的混乱程度；
- 也更容易定位具体失败条目。

### 7.3 加入 `summary.partial.json`

这是一个很重要的“阶段性容错”设计。

因为总共有数百条 episode，单次运行时间很长。若中途断掉，至少前面已经写入 `summary.partial.json` 的结果不会丢失，可以直接：

- 回看阶段指标；
- 抽查已完成条目；
- 再决定是否继续跑。

### 7.4 产物结构标准化

当前每条 episode 的结果目录结构已经比较规整，适合后续做：

- 人工抽样看视频；
- 定位动作错误；
- 对比预测轨迹；
- 二次统计指标。

---

## 8. 评估范围

### 8.1 评估任务类型

本次运行的是：

- **VLN unseen evaluation**

也就是在 unseen 场景/轨迹清单上测试模型导航能力。

### 8.2 episode 总数

根据当前运行配置，这批任务总数为：

- **534 个 episode**

### 8.3 当前阶段统计范围

在本次阶段总结撰写时，已经单独对：

- **前 89 个已完成 episode**

做了指标汇总。

相应统计文件为：

- `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141/metrics_summary_first_89.md`

这个统计反映的是**阶段性结果快照**，并不代表整批 534 个 episode 已全部跑完。

---

## 9. 当前阶段结果

### 9.1 前 89 个 episode 的总体均值

根据已经生成的统计文件，前 89 个 episode 的平均指标如下：

- 平均 `NE`：`6.413310`
- 平均 `nDTW`：`0.095040`
- 平均 `SR`：`0.022472`
- 平均 `OSR`：`0.022472`
- 平均 `final_dist`：`6.413310`
- 平均 `final_angle_diff`：`1.490321`
- 平均 `pred_steps`：`67.247191`
- 平均 `gt_path_length`：`18.974717`

这说明：

1. 在当前已完成的前 89 个样本中，整体导航误差仍然偏大；
2. 成功样本数较少；
3. 但已经出现了少量成功 episode，说明链路和指标判定是正常工作的。

### 9.2 已观察到的成功样本

在前 89 个 episode 中，平均 `SR = 0.022472`，说明约有 2 条左右成功样本。

当前已统计到的代表性成功样本包括：

1. `/gibson_2/Scioto/traj_-2/instruction.json`
   - `NE = 1.741517`
   - `SR = 1`
   - `OSR = 1`

2. `/gibson_1/Micanopy/traj_4/instruction_pro.json`
   - `NE = 1.791836`
   - `SR = 1`
   - `OSR = 1`

### 9.3 当前表现较好的样本

#### 按 `NE` 最好（越小越好）

当前前几名包括：

1. `/gibson_2/Scioto/traj_-2/instruction.json`
2. `/gibson_1/Micanopy/traj_4/instruction_pro.json`
3. `/gibson_2/Placida/traj_-1/instruction.json`
4. `/gibson_1/Brevort/traj_2/instruction.json`
5. `/gibson_1/Micanopy/traj_1/instruction.json`

#### 按 `nDTW` 最好（越大越好）

当前前几名包括：

1. `/gibson_2/Placida/traj_1/instruction.json`
2. `/gibson_1/Micanopy/traj_3/instruction_pro.json`
3. `/gibson_1/Micanopy/traj_4/instruction_pro.json`
4. `/gibson_2/Scioto/traj_-5/instruction.json`
5. `/gibson_2/Scioto/traj_-4/instruction.json`

### 9.4 当前结果应如何理解

从阶段结果来看，这次工作最重要的成果并不是“已经把指标做到很高”，而是：

- **建立了一套可稳定批跑的 unseen VLN 评测工程流程**；
- 可以持续输出结构化结果；
- 可以逐条回看视频与轨迹；
- 可以实时形成阶段统计；
- 可以后续继续扩展为完整 534 条的总体评测结果。

换句话说，这次工作的价值首先体现在**工程闭环**已经建立，其次才是具体指标数值本身。

---

## 10. 结果文件与成果文件说明

本次运行的主结果目录位于：

- `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141`

其中主要文件和子目录如下。

### 10.1 运行级文件

#### `manifest_used.json`

保存本次运行实际使用的 manifest 备份，便于后续确认评估输入。

#### `original_test_vln_unseen.json`

保存运行前原始 active manifest 的备份，用于恢复或对照。

#### `current_episode_manifest.json`

保存当前 episode 的临时 manifest。运行中会被反复覆盖。

#### `summary.partial.json`

阶段性汇总文件。每完成一条 episode 就更新一次，是本次长任务中最重要的过程性统计文件。

#### `summary.json`

整批完成后的完整汇总文件。若任务尚未全部完成，则当前更有参考价值的是 `summary.partial.json`。

#### `overall_metrics.json`

整批运行结束后的总体平均指标文件，包括：

- `average_NE`
- `success_rate`
- `online_success_rate`
- `average_nDTW`

### 10.2 `episodes/` 目录

每个子目录对应一个独立的 episode，例如：

- `episodes/0001__gibson_1_Brevort_traj_-1_instruction.json/`

单条 episode 目录下当前已确认包含：

#### `episode.mp4`

该条 episode 的视频文件，由运行中保存的图片序列导出而来，可直接用于可视化回看。

#### `interaction_actions.json`

该条 episode 的动作轨迹/交互轨迹摘要，包括：

- episode key
- steps
- termination_reason
- instructions
- final_instruction_index
- trajectory

#### `metrics.json`

该条 episode 的评价指标，包括：

- `NE`
- `SR`
- `OSR`
- `nDTW`
- `final_dist`
- `final_angle_diff`
- `gt_path_length`
- `pred_steps`

#### `shared_folder/`

保留本条 episode 运行时的中间目录备份，用于问题定位与二次分析。其内部通常包含：

- `images/`
- `sim_input/`
- `sim_output/`
- `model_input/`
- `model_output/`
- `controller_input/`
- `instructions/`
- `trajectories/`

其中 `shared_folder/trajectories/` 下会保存预测轨迹相关文件，例如：

- `_{episode_name}.json`
- `final_results.json`

### 10.3 `logs/` 目录

每条 episode 会生成三类日志：

- `xxxx_model.log`
- `xxxx_sim.log`
- `xxxx_controller.log`

这些日志对于定位以下问题非常有帮助：

- 模型是否正常启动；
- 仿真器是否正常加载；
- controller 是否卡住；
- 当前 episode 为什么超时或提前结束。

### 10.4 额外统计文件

本次还额外生成了一个阶段性统计文档：

- `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141/metrics_summary_first_89.md`

它对当前前 89 个 episode 进行了：

- 总体均值统计；
- 极值统计；
- Top 10 by NE；
- Top 10 by nDTW。

该文件适合作为阶段汇报材料的基础版本。

---

## 11. 本次工作的阶段性结论

从工程实施角度看，这次项目已经取得了明确的阶段成果：

1. `IndoorUAV-Agent` 的 unseen VLN 评测链路已经跑通；
2. 已构建出按 episode 独立归档的 `v2` 批处理脚本；
3. 每条 episode 都能稳定产出：
   - 视频；
   - 动作轨迹；
   - 预测轨迹；
   - 评价指标；
4. 已支持阶段性统计汇总，而不必等待整批 534 条全部结束；
5. 已识别出存储设计上的关键风险：
   - 最终结果在数据盘；
   - 中间工作目录和历史缓存仍会消耗系统盘；
6. 已形成一份前 89 个 episode 的量化总结文档，适合作为当前实验快照。

从结果角度看，当前模型在 unseen VLN 上已经能够完成少量成功导航，但总体成功率仍较低，后续还需要：

- 继续跑完整批 534 条，得到更稳定的总体结论；
- 结合视频与轨迹分析失败模式；
- 重点比较 instruction / instruction_pro 的差异；
- 对表现较好与较差场景做更细粒度拆解。

---

## 12. 后续建议

结合本次经验，后续如果继续推进，建议优先做以下几件事：

### 12.1 完整跑完 534 个 episode

当前前 89 条只是阶段结果，完整结论仍需等全部 unseen episode 结束后再看 `overall_metrics.json`。

### 12.2 把运行时工作目录也迁到数据盘

当前最值得做的工程优化，不是再加新指标，而是把：

- `shared_folder`
- 可能的缓存目录
- 大型中间数据目录

也同步迁移到数据盘。否则即使结果目录在 `/data1`，系统盘仍会被运行时文件和历史缓存顶满。

### 12.3 对成功/失败样本做专题分析

建议从 `metrics_summary_first_89.md` 中选：

- 最好样本；
- 最差样本；
- nDTW 高但未成功样本；
- NE 小但路径偏差仍明显样本；

逐条回看：

- 视频；
- 动作轨迹；
- 预测轨迹；
- 对应日志；

这样更容易定位模型究竟是：

- 理解指令有问题；
- 视觉感知有问题；
- 轨迹规划有问题；
- 还是结束判定/控制链路存在问题。

### 12.4 保留阶段性统计机制

`summary.partial.json` 和单独生成的 Markdown 统计文件非常有价值，建议后续继续保留这种机制，因为它能显著降低长时间任务的不可控性。

---

## 13. 总结

这次项目的核心成果，可以概括为一句话：

> 我们已经把 `IndoorUAV-Agent` 的 unseen VLN 在线评测，从“原始仓库脚本能跑”推进到了“可批量、可归档、可统计、可回溯”的工程化阶段。

虽然当前阶段性指标还不能说明模型在 unseen VLN 上已经表现优秀，但从实验工程角度看，整个闭环已经搭建起来了：

- 有清晰的数据输入；
- 有稳定的多进程评测链路；
- 有逐条 episode 的结果落盘；
- 有自动指标计算；
- 有阶段性统计文档；
- 有可回溯的视频、日志和轨迹产物。

这为后续继续跑完整个 unseen 集、做失败分析、优化模型和对比不同配置，已经打下了足够扎实的基础。

