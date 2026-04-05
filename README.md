# IndoorUAV-Agent VLN Unseen Evaluation

> We evaluated the VLN ability for `IndoorUAV-Agent`, used the pre-train model and dataset by this open-source repository.

<br>

**1.We made a brielfly survay for avaliable VLN or VLA resorces and papers, espacially in domain of UAV, find these valuable:**

- A bunch of papers and codes gathering in https://github.com/TheBrainLab/Awesome-VLA-UAVs, we search avaliable repositories here
- An ICLR 2025 open-source work: https://prince687028.github.io/OpenUAV, but the code in https://github.com/prince687028/TravelUAV seems lacking of a pre-trained weight, so we don't choose it
- A HRI 2025 work: https://github.com/sautenich/uav-vla, seems easy to use by OpenAI key but do not have original datasets, so we don't choose it
- Seems to be a software with CV nor VLA: https://github.com/puku0x/cvdrone

<br>

**2.Mainly used resoueces**

We finally find an AAAI 26 paper with the whole open-source code/dataset/model/pre-trained weight, so finally choose it for the experiment:
**IndoorUAV: Benchmarking Vision-Language UAV Navigation in Continuous Indoor Environments**
- paper: https://arxiv.org/abs/2512.19024
- code: https://github.com/valyentinee/IndoorUAV-Agent
- dataset: https://www.modelscope.cn/datasets/valyentine/Indoor_UAV
- pre-trained weight: https://modelscope.cn/models/valyentine/IndoorUAV-Agent/files

The repository mainly relies on two important basements:
- the physics-enabled 3D simulator: https://github.com/facebookresearch/habitat-sim
- the famous VLA work pi_0 : https://github.com/Physical-Intelligence/openpi

<br>

**3.Implementation**
- Platform: We use AutoDL service for the task with PyTorch 2.7.0, Python 3.12(ubuntu22.04), CUDA 12.8, RTX 5090(32GB)*1, 25 vCPU Intel(R) Xeon(R) Platinum 8470Q, RAM 90GB, Storage 30+50+130 GB. If you want to reproduce, this is an avaliable choice.
- Envs: We use the base env for IndoorUAV+openpi, use conda venv for habitate-sim. A keypoint is habitate-sim should install via conda and I try to compile it then fail. A thinghua source speedup for some of the packages is neccesary.
- Dataset & pre-trained weight: They can be downloaded directly in the link via web/cmd, or by it's conda guildence. The weight is about 10GB; and the whole dataset with training and evaluation sets is about 1.38TB, devided into many sub-zips that could not be unpackaged with anyone singlely. Here, the `scene_datasets.zip` with 47GB is nessecary for simulation scene, and the `without_screenshot.zip` with 500MB is the smallest package of dataset we could use that only with prompts and ground truth trajectories. So I only download these two for the evaluation.
- Smoketest: The `IndoorUAV-Agent` repo tells how to use the training and eval pipline, I think with the whole dataset we can easily do this. But for the storage limit (I need to pay ￥1 per day for the extra 130GB storage in the service), I could only do evaluation by the least dataset. With a modification with the eval pipline, the smoketest with random init pic tensor could get an output, with fixing for the personal path in the origin repo.
- Evaluation: With smoketest, an eval pipline is generated for the without_screenshot. The 89/534 task in it have been tested.
- Result: Only 2/89 episodes succeed for reaching the orientaion, and nearly all of them fail for the tasks, the metrics are pool.

<br>

**4.Remark**
It seems in without_screenshot dataset the currently pre-trained model nearly fail, means the VAN ability need be improved in the following works, should consider a world model or better pre-trained model (I think the used base model is too wake and small) or try diffusion policy and inverse dynamic action generation. Additionally and interesting, I find these fail modes by checking the eval videos:
- Prompt: ascende, failed by ascending too high to ceil.
- Prompt: reach near the door, failed by reaching not enough so could not do the following turn right task.
- Prompt: find something, failed by interfered by scene of obstacles or limited vision, so it interrupt the right action and walk or turn around suddently.
- Clipping: Aircraft crossing simulator scene boundary leads to failure.

<br>

**5.Method of IndoorUAV**
- Dataset: 1075 3D indoor scenes from Habitat, manual trajectory collection + augmentation, GPT-4o for multi-granularity annotation, 50965 trajectories with images/poses, split into VLN/VLA subsets.
- Method: Build IndoorUAV-Agent, VLA infers trajectory via fine-tuned π₀, VLN decomposes long instructions into sub-instructions by GPT-4o, executes subtasks with VLA sequentially and updates visual states.
- Metrics: Adopt SR, NDTW, NE, OSR to evaluate model performance in seen/unseen scenes.

<br>

**6.Example**
```
"/hm3d_13/UfhK7KNBg5u/traj_-2/instruction_pro.json": [
    "Starting at the entrance of the living room before a distant door on the left and a table, lamp, and window on the right, ascend to bring the door and window into near view",
    "fly forward through the entrance until no prominent objects remain",
    "turn left toward a nearby closet with a doorway and sink ahead",
    "fly forward to approach a cabinet and sink beneath a mirror",
    "continue forward toward the sink and cabinet past the right-side door",
    "turn right toward a sofa beside a table with a window beyond",
    "fly into the bedroom to approach a table and lamp flanked by a door and toilet on the left and a bed with pillows on the right",
    "fly forward again to reveal a painting on the right wall",
    "turn right back into the living room facing a chair with a vase and a distant painting and window beyond",
    "fly onto the porch to draw alongside a gutter on the left, pole ahead, and roof overhead with bushes lining the sides and houses beyond",
    "and finally descend in front of the porch door"
  ],
```

---

The follwing are summerized by gpt-5.4-thinking.

> An engineering report for running and analyzing large-scale episode-by-episode VLN evaluation with `IndoorUAV-Agent`.

## Overview

This document summarizes a staged evaluation project built on top of the `IndoorUAV-Agent` repository. The goal was not to retrain the model from scratch, but to turn the original online VLN evaluation workflow into a more robust, inspectable, and resumable evaluation pipeline.

In particular, the project focused on:

- running the `IndoorUAV-Agent` VLN unseen evaluation end-to-end;
- converting the evaluation into an **episode-by-episode** pipeline;
- saving per-episode artifacts, including video, action traces, predicted trajectories, and metrics;
- moving final outputs to a data disk to reduce pressure on the system disk;
- generating stage-level summaries before the full unseen set finishes.

At the time of writing, the pipeline has already produced structured results for the first **89 completed episodes** out of **534 total unseen VLN episodes**.

---

## Repository and Dependencies

### Main repository

This project is based on:

- `IndoorUAV-Agent`

Repository path used in this run:

- `/root/AAE5303/IndoorUAV-Agent`

According to the original project documentation, the repository provides:

- pretrained `IndoorUAV-Agent` checkpoints;
- online evaluation scripts for VLA and VLN tasks;
- metric evaluation utilities;
- fine-tuning configuration and references;
- integration with `openpi` and `Habitat-Sim`.

### Related components

The evaluation pipeline depends on two major external components:

#### 1. `openpi`

Used for the inference/model side of the system. In this project it provides the model runtime environment and associated configuration.

#### 2. `Habitat-Sim`

Used for continuous indoor simulation. It is responsible for:

- loading scenes;
- simulating the UAV;
- rendering observations;
- producing state transitions and trajectory evolution.

### Dataset

The evaluation uses the IndoorUAV dataset assets referenced by the official repository, including:

- scene datasets;
- `without_screenshot` trajectories and posture annotations;
- instruction manifests for unseen VLN evaluation.

In this evaluation flow:

- `test_vln_unseen.json` is used as the unseen VLN manifest;
- `without_screenshot/.../posture.json` is used as the ground-truth trajectory source;
- `shared_folder/` is used as the runtime exchange directory among simulator, controller, and model processes.

---

## Evaluation Goal

The purpose of this work was to establish a practical and reproducible evaluation workflow for the **VLN unseen split**.

Rather than launching one large monolithic evaluation run, the system was redesigned to:

1. run **one episode at a time**;
2. archive outputs per episode;
3. compute metrics immediately after each episode finishes;
4. maintain a running partial summary;
5. make it easy to inspect failures and successful cases with videos and logs.

This engineering-oriented design is especially useful for long-running evaluations with hundreds of episodes.

---

## Core Script

The main script used in this project is:

- `run_vln_unseen_eval_v2.py`

This script was used as a custom episode-level evaluator on top of the original repository.

Its main responsibilities are:

1. load the unseen VLN manifest;
2. iterate over episodes one by one;
3. launch the three required services for each episode:
   - `model_runner.py`
   - `sim_runnner.py`
   - `vln_controller.py`
4. wait until the trajectory file for the current episode is produced;
5. terminate the running services;
6. export a video for the episode;
7. build an action trace JSON;
8. compute VLN metrics using the predicted trajectory and ground-truth posture;
9. archive intermediate files under a dedicated per-episode folder;
10. continuously write `summary.partial.json`.

This design makes the evaluation process much easier to debug and much safer for long unattended runs.

---

## End-to-End Pipeline

The full pipeline used in this project can be summarized as follows.

### Step 1. Prepare a single-episode manifest

Although the unseen split contains hundreds of episodes, the script extracts only one episode at a time and writes it into:

- `current_episode_manifest.json`

It then replaces the active manifest used by the evaluation controller.

This allows the whole unseen benchmark to be executed in a strictly sequential, per-episode manner.

### Step 2. Launch the three services

For each episode, the following services are started in sequence:

1. `model_runner.py`
2. `sim_runnner.py`
3. `vln_controller.py`

These services communicate through `shared_folder/`.

The exchange includes:

- images rendered by the simulator;
- model input/output files;
- controller-side inputs;
- generated trajectory files.

### Step 3. Wait for the episode result

The script polls the trajectory output path:

- `shared_folder/trajectories/{episode_name}.json`

Once the file appears, the episode is treated as finished.

If the file does not appear before timeout, the episode is marked as failed and the error is recorded.

### Step 4. Archive outputs for that episode

After completion, the pipeline creates a dedicated folder such as:

- `episodes/0001__gibson_1_Brevort_traj_-1_instruction.json/`

Inside that folder, the pipeline stores:

- `episode.mp4`
- `interaction_actions.json`
- `metrics.json`
- `shared_folder/` backup

### Step 5. Update partial summary

After every episode, the system updates:

- `summary.partial.json`

This is crucial for long-running jobs, because it allows progress tracking and staged analysis even if the full run is not finished yet.

When the full run eventually ends, the script also writes:

- `summary.json`
- `overall_metrics.json`

---

## Environment Setup Strategy

The original repository requires **two separate environments**, because the simulator environment and the model inference environment are not compatible.

### Simulator environment

Used for:

- `sim_runnner.py`
- `vln_controller.py`

Environment name used in this project:

- `habitat`

### Inference environment

Used for:

- `model_runner.py`

Environment name used in this project:

- `base`

### Installation references

Following the official repository guidance, the environment setup is based on:

- Habitat-Sim installation instructions for the simulator side;
- the repository-provided `openpi/README.md` for the inference side;
- manual configuration of:
  - dataset paths,
  - model checkpoint path,
  - scene dataset path,
  - training metadata path.

### Practical launch method in this project

Instead of manually coordinating several terminals, the project uses a Python-managed process launcher. Each episode internally runs commands equivalent to:

```bash
source /root/miniconda3/etc/profile.d/conda.sh
conda activate base
conda activate habitat
```

and starts the services using `subprocess.Popen`.

This has several advantages:

- less manual intervention;
- easier batch execution;
- clear per-episode lifecycle;
- better support for unattended evaluation.

---

## Main Engineering Challenges

Several practical issues appeared during the project.

### 1. The default result directory was on the system disk

Initially, the result directory defaulted to a repository-local path such as `result/`, which means all outputs were written to the system disk.

This was later changed so that final results are stored on a data disk:

- `/data1/liuy/IndoorUAV-Agent-result`

This reduced pressure on the system disk for archived outputs.

### 2. Argument mis-editing during manual changes

While adjusting the custom script, there was a temporary issue where:

- `--result-dir` was accidentally defined twice;
- `--manifest` was temporarily missing or overwritten.

This kind of mistake can break argument parsing and downstream file resolution.

The final working argument layout includes:

- `--repo-root`
- `--result-dir`
- `--manifest`
- `--base-env`
- `--habitat-env`
- `--limit`
- `--start-index`
- `--fps`

### 3. The system disk filled up even after moving results to the data disk

This was one of the most important findings in the project.

At first glance, it looked confusing: final results were already being written to the data disk, yet the system disk still filled up quickly.

The reason is that **moving the final result directory is not the same as moving runtime working directories**.

While archived outputs were saved under `/data1`, runtime data was still being written under locations such as:

- `/root/AAE5303/IndoorUAV-Agent/shared_folder`
- `/tmp`
- `/root/autodl-tmp`

As a result:

- archived episode outputs grew on the data disk;
- runtime exchange files, caches, and historical temporary data continued to consume the system disk.

This explains why the system disk filled up much faster than expected.

### 4. Verifying whether each episode produced a complete artifact set

To make sure the new evaluation pipeline was truly usable, completed episode folders were inspected to confirm that each one contained at least:

- a video;
- an action trace;
- a predicted trajectory;
- evaluation metrics.

This check passed for completed samples in the current run.

---

## Solutions Adopted

The following engineering decisions stabilized the workflow.

### 1. Move final results to the data disk

The result directory was changed to:

- `/data1/liuy/IndoorUAV-Agent-result`

This keeps archived artifacts such as videos, metrics, per-episode backups, and summaries off the system disk.

### 2. Use sequential per-episode evaluation

Instead of one giant batch process, the `v2` evaluator runs one episode at a time.

Advantages:

- isolated episode execution;
- easier debugging;
- less cross-episode contamination;
- simpler failure localization.

### 3. Keep a running partial summary

The project continuously writes:

- `summary.partial.json`

This acts as a fault-tolerant progress checkpoint for long evaluation runs.

Even if the job stops halfway, the completed episodes are already summarized and available for analysis.

### 4. Standardize per-episode artifacts

Each completed episode now has a consistent directory layout, which makes it much easier to:

- inspect videos;
- compare trajectories;
- read logs;
- compute secondary statistics later.

---

## Evaluation Scope

### Task

This project runs:

- **VLN unseen evaluation**

### Total number of episodes

The configured unseen benchmark contains:

- **534 episodes**

### Current stage covered in this report

At the current stage, a dedicated summary has been generated for:

- **the first 89 completed episodes**

The staged summary file is:

- `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141/metrics_summary_first_89.md`

This should be understood as a **snapshot of progress**, not the final result of the full unseen benchmark.

---

## Current Results (First 89 Completed Episodes)

The staged summary over the first 89 completed episodes reports the following mean values:

| Metric | Value |
|---|---:|
| Average NE | 6.413310 |
| Average nDTW | 0.095040 |
| Average SR | 0.022472 |
| Average OSR | 0.022472 |
| Average final distance | 6.413310 |
| Average final angle difference | 1.490321 |
| Average predicted steps | 67.247191 |
| Average GT path length | 18.974717 |

### Interpretation

These numbers suggest that:

1. the full evaluation pipeline is functioning correctly;
2. a small number of successful episodes have already appeared;
3. overall unseen VLN performance is still limited at this stage.

In other words, the main success of the current stage is **engineering completion and experimental observability**, rather than strong benchmark performance.

---

## Representative Successful Episodes

Among the first 89 completed episodes, the average `SR` is `0.022472`, which means roughly two successful episodes were observed.

Examples include:

### `/gibson_2/Scioto/traj_-2/instruction.json`

- `NE = 1.741517`
- `SR = 1`
- `OSR = 1`

### `/gibson_1/Micanopy/traj_4/instruction_pro.json`

- `NE = 1.791836`
- `SR = 1`
- `OSR = 1`

These cases are useful starting points for qualitative analysis.

---

## Best Episodes Observed So Far

### Top examples by NE (lower is better)

The strongest episodes so far by navigation error include:

1. `/gibson_2/Scioto/traj_-2/instruction.json`
2. `/gibson_1/Micanopy/traj_4/instruction_pro.json`
3. `/gibson_2/Placida/traj_-1/instruction.json`
4. `/gibson_1/Brevort/traj_2/instruction.json`
5. `/gibson_1/Micanopy/traj_1/instruction.json`

### Top examples by nDTW (higher is better)

The strongest episodes so far by trajectory similarity include:

1. `/gibson_2/Placida/traj_1/instruction.json`
2. `/gibson_1/Micanopy/traj_3/instruction_pro.json`
3. `/gibson_1/Micanopy/traj_4/instruction_pro.json`
4. `/gibson_2/Scioto/traj_-5/instruction.json`
5. `/gibson_2/Scioto/traj_-4/instruction.json`

This shows that different metrics highlight different kinds of good behavior: some episodes finish closer to the target, while others better match the overall GT path structure.

---

## Output Artifacts

The main output directory of this run is:

- `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141`

### Run-level files

#### `manifest_used.json`

A backup of the manifest actually used in the run.

#### `original_test_vln_unseen.json`

A backup of the original active unseen manifest before replacement.

#### `current_episode_manifest.json`

The temporary single-episode manifest used during execution.

#### `summary.partial.json`

The most important staged summary file. It is updated after every completed episode.

#### `summary.json`

The final run summary written when the full run finishes.

#### `overall_metrics.json`

The final run-level aggregate metrics file, expected to contain fields such as:

- `average_NE`
- `success_rate`
- `online_success_rate`
- `average_nDTW`

### Per-episode folders under `episodes/`

Each episode gets its own directory, for example:

- `episodes/0001__gibson_1_Brevort_traj_-1_instruction.json/`

A typical episode folder contains:

#### `episode.mp4`

A rendered video of the episode built from simulator image frames.

#### `interaction_actions.json`

A compact action/interaction trace containing:

- episode key;
- number of steps;
- termination reason;
- instructions;
- final instruction index;
- trajectory.

#### `metrics.json`

Episode-level metrics, including:

- `NE`
- `SR`
- `OSR`
- `nDTW`
- `final_dist`
- `final_angle_diff`
- `gt_path_length`
- `pred_steps`

#### `shared_folder/`

A backup of the runtime exchange folder for that episode. It typically includes:

- `images/`
- `sim_input/`
- `sim_output/`
- `model_input/`
- `model_output/`
- `controller_input/`
- `instructions/`
- `trajectories/`

The `trajectories/` directory usually contains files such as:

- `_{episode_name}.json`
- `final_results.json`

### Logs

The `logs/` directory stores three logs per episode:

- `xxxx_model.log`
- `xxxx_sim.log`
- `xxxx_controller.log`

These logs are useful for diagnosing:

- model startup issues;
- simulator loading failures;
- controller stalls;
- timeout cases;
- abnormal early termination.

### Extra staged report

An additional staged report was generated for the first 89 completed episodes:

- `/data1/liuy/IndoorUAV-Agent-result/unseen_eval_v2_20260405_192141/metrics_summary_first_89.md`

This file contains:

- mean metric statistics;
- extrema;
- top 10 by NE;
- top 10 by nDTW.

---

## What This Project Has Achieved So Far

From an engineering perspective, this project has already achieved several important milestones:

1. the `IndoorUAV-Agent` unseen VLN evaluation pipeline runs end-to-end;
2. a custom **episode-by-episode v2 evaluator** has been built;
3. each episode can now produce a complete artifact package:
   - video,
   - action trace,
   - predicted trajectory,
   - metrics;
4. staged summaries can be generated before the full 534-episode run completes;
5. disk usage issues have been partially mitigated by moving final outputs to the data disk;
6. a structured experimental snapshot for the first 89 completed episodes has already been produced.

From a benchmarking perspective, current performance is still modest, but the experiment infrastructure is now solid enough to support:

- full unseen evaluation;
- failure analysis;
- successful-case analysis;
- comparison between `instruction` and `instruction_pro` variants;
- future model or pipeline improvements.

---

## Limitations and Lessons Learned

This project also revealed some practical limitations.

### Runtime files still consume the system disk

Even though final results are now stored on the data disk, runtime exchange directories and temporary caches still consume the system disk.

This means that moving only the final output directory is not sufficient for truly large-scale evaluation.

### Current metrics reflect only a partial run

The staged summary covers only the first 89 completed episodes, not the full 534-episode benchmark. Final conclusions should be drawn only after the entire unseen split has finished.

### Performance is not yet the main takeaway

At this stage, the strongest contribution is the engineering pipeline itself:

- resumable,
- inspectable,
- per-episode archived,
- metrics-aware,
- suitable for large-scale debugging and analysis.

---

## Recommended Next Steps

Based on the current progress, the following next steps are recommended.

### 1. Finish the full 534-episode unseen run

The most immediate next step is to let the full evaluation finish and analyze `overall_metrics.json`.

### 2. Move runtime working directories to the data disk as well

To avoid future system disk exhaustion, it would be beneficial to move directories such as:

- `shared_folder`
- temporary cache directories
- other large runtime intermediates

onto the data disk too.

### 3. Perform qualitative case analysis

A strong next analysis direction is to inspect:

- the best episodes;
- the worst episodes;
- episodes with high nDTW but failed success criteria;
- episodes with low NE but poor overall path quality.

For each selected case, inspect:

- the video;
- the action trace;
- the predicted trajectory;
- the logs.

This can help determine whether the dominant failure mode comes from:

- instruction understanding,
- visual grounding,
- trajectory planning,
- controller behavior,
- or stopping criteria.

### 4. Keep the staged reporting mechanism

The combination of `summary.partial.json` and staged Markdown reports is extremely useful for long-running experiments and should be kept in future versions of the evaluation pipeline.

---

## Conclusion

The key outcome of this work can be summarized in one sentence:

> The `IndoorUAV-Agent` unseen VLN evaluation has been upgraded from a runnable repository workflow into a batch-capable, per-episode archived, metrics-aware, and analysis-friendly evaluation system.

Although the current staged metrics do not yet indicate strong unseen VLN performance, the experimental loop is now complete:

- clear inputs,
- stable multi-process execution,
- archived episode outputs,
- automatic metric computation,
- staged summary reporting,
- and traceable videos, logs, and trajectories.

This provides a solid foundation for completing the full unseen benchmark, conducting failure analysis, comparing configurations, and improving the model in future iterations.

