# 前 89 个 episode 指标统计

- 统计时间: 自动生成
- 结果目录: `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141`
- 纳入统计的 episode 数: `89`
- 有效 metrics 数: `89`

## 总体均值

| 指标 | 数值 |
|---|---:|
| 平均 NE | 6.413310 |
| 平均 nDTW | 0.095040 |
| 平均 SR | 0.022472 |
| 平均 OSR | 0.022472 |
| 平均 final_dist | 6.413310 |
| 平均 final_angle_diff | 1.490321 |
| 平均 pred_steps | 67.247191 |
| 平均 gt_path_length | 18.974717 |

## 极值

- 最小 NE: `1.741517` -> `/gibson_2/Scioto/traj_-2/instruction.json`
- 最大 nDTW: `0.475174` -> `/gibson_2/Placida/traj_1/instruction.json`
- 最大 NE: `36.913302` -> `/gibson_2/Placida/traj_2/instruction_pro.json`

## Top 10 by NE（越小越好）

| Rank | Index | Episode | NE | nDTW | SR | OSR | pred_steps |
|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 73 | `/gibson_2/Scioto/traj_-2/instruction.json` | 1.741517 | 0.201530 | 1 | 1 | 52 |
| 2 | 56 | `/gibson_1/Micanopy/traj_4/instruction_pro.json` | 1.791836 | 0.311298 | 1 | 1 | 60 |
| 3 | 63 | `/gibson_2/Placida/traj_-1/instruction.json` | 3.091672 | 0.144411 | 0 | 0 | 31 |
| 4 | 5 | `/gibson_1/Brevort/traj_2/instruction.json` | 3.280657 | 0.078645 | 0 | 0 | 47 |
| 5 | 49 | `/gibson_1/Micanopy/traj_1/instruction.json` | 3.317644 | 0.036439 | 0 | 0 | 39 |
| 6 | 64 | `/gibson_2/Placida/traj_-1/instruction_pro.json` | 3.328536 | 0.152891 | 0 | 0 | 36 |
| 7 | 34 | `/gibson_1/Albertville/traj_2/instruction_pro.json` | 3.333749 | 0.064885 | 0 | 0 | 42 |
| 8 | 66 | `/gibson_2/Placida/traj_-2/instruction_pro.json` | 3.492527 | 0.124166 | 0 | 0 | 49 |
| 9 | 38 | `/gibson_1/Albertville/traj_4/instruction_pro.json` | 3.519118 | 0.051406 | 0 | 0 | 55 |
| 10 | 10 | `/gibson_1/Eagerville/traj_-1/instruction_pro.json` | 3.540973 | 0.078464 | 0 | 0 | 139 |

## Top 10 by nDTW（越大越好）

| Rank | Index | Episode | nDTW | NE | SR | OSR | pred_steps |
|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 67 | `/gibson_2/Placida/traj_1/instruction.json` | 0.475174 | 3.600168 | 0 | 0 | 38 |
| 2 | 54 | `/gibson_1/Micanopy/traj_3/instruction_pro.json` | 0.332352 | 5.899117 | 0 | 0 | 29 |
| 3 | 56 | `/gibson_1/Micanopy/traj_4/instruction_pro.json` | 0.311298 | 1.791836 | 1 | 1 | 60 |
| 4 | 79 | `/gibson_2/Scioto/traj_-5/instruction.json` | 0.259800 | 3.783829 | 0 | 0 | 34 |
| 5 | 77 | `/gibson_2/Scioto/traj_-4/instruction.json` | 0.247007 | 4.601388 | 0 | 0 | 32 |
| 6 | 78 | `/gibson_2/Scioto/traj_-4/instruction_pro.json` | 0.240852 | 4.188051 | 0 | 0 | 15 |
| 7 | 16 | `/gibson_1/Arkansaw/traj_-2/instruction_pro.json` | 0.218923 | 3.719568 | 0 | 0 | 133 |
| 8 | 62 | `/gibson_1/Micanopy/traj_7/instruction_pro.json` | 0.209729 | 5.859670 | 0 | 0 | 34 |
| 9 | 73 | `/gibson_2/Scioto/traj_-2/instruction.json` | 0.201530 | 1.741517 | 1 | 1 | 52 |
| 10 | 58 | `/gibson_1/Micanopy/traj_5/instruction_pro.json` | 0.200385 | 5.106550 | 0 | 0 | 28 |

## 备注

- 当前统计基于 `summary.partial.json` 中前 89 个已完成 episode。
- 因为当前已完成样本中 SR/OSR 基本为 0，所以更适合重点看 `NE` 和 `nDTW`。
