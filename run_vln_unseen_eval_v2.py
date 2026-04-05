#!/usr/bin/env python3
import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean


THRESHOLD_SUCCESS_DIST = 2
THRESHOLD_SUCCESS_ANGLE = math.pi * 2
ALPHA = 10
POLL_INTERVAL = 2.0
EPISODE_TIMEOUT_SECONDS = 360
STARTUP_WAIT_SECONDS = 8


def angle_difference(a, b):
    diff = abs(a - b)
    return min(diff, 2 * math.pi - diff)


def calculate_ndtw(seq_a, seq_b):
    if len(seq_a) == 0 or len(seq_b) == 0:
        return 0.0, 0.0
    distance, _ = fastdtw(np.array(seq_a), np.array(seq_b), dist=euclidean)
    ref_length = sum(euclidean(seq_b[i], seq_b[i - 1]) for i in range(1, len(seq_b)))
    ref_length = max(ref_length, 1e-5)
    return math.exp(-distance / (ALPHA * ref_length)), ref_length


def safe_episode_name(episode_key: str) -> str:
    return episode_key.replace('/', '_').replace(':', '_').replace(' ', '_')


def ensure_empty_shared_folder(shared_folder: Path):
    if shared_folder.exists():
        shutil.rmtree(shared_folder)
    for rel in [
        'images',
        'sim_input',
        'sim_output',
        'model_input',
        'model_output',
        'controller_input',
        'instructions',
        'trajectories',
    ]:
        (shared_folder / rel).mkdir(parents=True, exist_ok=True)


def write_single_episode_manifest(path: Path, episode_key: str, instructions):
    with path.open('w', encoding='utf-8') as f:
        json.dump({episode_key: instructions}, f, ensure_ascii=False, indent=2)


def wait_for_episode_result(shared_folder: Path, episode_key: str, timeout_seconds: int):
    trajectory_name = f"{safe_episode_name(episode_key)}.json"
    trajectory_path = shared_folder / 'trajectories' / trajectory_name
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if trajectory_path.exists():
            return trajectory_path
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f'等待 episode 结果超时: {episode_key}')


def kill_process(proc: subprocess.Popen | None):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
            proc.wait(timeout=5)


def start_service(conda_sh: Path, env_name: str, script_path: Path, cwd: Path, log_path: Path):
    command = (
        f'source "{conda_sh}" && '
        f'conda activate {env_name} && '
        f'cd "{cwd}" && '
        f'python "{script_path}"'
    )
    log_file = log_path.open('w', encoding='utf-8')
    proc = subprocess.Popen(
        ['bash', '-lc', command],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(cwd),
        text=True,
        preexec_fn=os.setsid,
    )
    return proc, log_file


def export_video(images_dir: Path, output_path: Path, fps: int = 6):
    pngs = [p for p in images_dir.iterdir() if p.suffix.lower() == '.png']
    if not pngs:
        return None

    def sort_key(p: Path):
        stem = p.stem
        try:
            return float(stem.rsplit('_', 1)[-1])
        except ValueError:
            return stem

    pngs = sorted(pngs, key=sort_key)
    frames = [imageio.imread(p) for p in pngs]
    imageio.mimwrite(output_path, frames, fps=fps)
    return output_path


def build_action_trace(trajectory_json: Path, output_path: Path):
    with trajectory_json.open('r', encoding='utf-8') as f:
        data = json.load(f)

    action_trace = {
        'episode_key': data['episode_key'],
        'steps': data.get('steps', 0),
        'termination_reason': data.get('termination_reason'),
        'instructions': data.get('instructions', []),
        'final_instruction_index': data.get('current_instruction_index'),
        'trajectory': data.get('trajectory', []),
    }

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(action_trace, f, ensure_ascii=False, indent=2)

    return output_path


def compute_vln_metrics(trajectory_json: Path, without_screenshot_root: Path):
    with trajectory_json.open('r', encoding='utf-8') as f:
        data = json.load(f)

    episode_key = data['episode_key'].lstrip('/')
    pred_trajectory = data['trajectory']
    posture_path = without_screenshot_root / Path(os.path.dirname(episode_key)) / 'posture.json'

    with posture_path.open('r', encoding='utf-8') as f:
        gt_full_seq = json.load(f)

    gt_seq = []
    gt_positions = []
    for point in gt_full_seq:
        x, y, z, yaw_deg = point
        yaw_rad = yaw_deg * math.pi / 180.0
        gt_seq.append([x, y, z, yaw_rad])
        gt_positions.append([x, y, z])

    pred_positions = [point[:3] for point in pred_trajectory]
    gt_end = gt_seq[-1]
    pred_end = pred_trajectory[-1]

    final_dist = euclidean(pred_end[:3], gt_end[:3])
    final_angle_diff = angle_difference(pred_end[3], gt_end[3])
    sr = 1 if (final_dist <= THRESHOLD_SUCCESS_DIST and final_angle_diff <= THRESHOLD_SUCCESS_ANGLE) else 0

    osr = 0
    for point in pred_trajectory:
        dist = euclidean(point[:3], gt_end[:3])
        ang_diff = angle_difference(point[3], gt_end[3])
        if dist <= THRESHOLD_SUCCESS_DIST and ang_diff <= THRESHOLD_SUCCESS_ANGLE:
            osr = 1
            break

    ndtw, ref_length = calculate_ndtw(pred_positions, gt_positions)

    return {
        'episode_key': episode_key,
        'NE': final_dist,
        'SR': sr,
        'OSR': osr,
        'nDTW': ndtw,
        'final_dist': final_dist,
        'final_angle_diff': final_angle_diff,
        'gt_path_length': ref_length,
        'pred_steps': len(pred_trajectory),
    }


def save_json(data, output_path: Path):
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup_shared_folder(shared_folder: Path, destination: Path):
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(shared_folder, destination)


def main():
    parser = argparse.ArgumentParser(description='Run full unseen VLN eval pipeline episode-by-episode (v2).')
    parser.add_argument('--repo-root', default='/root/AAE5303/IndoorUAV-Agent')
    parser.add_argument('--result-dir', default='/data1/liuy/IndoorUAV-Agent-result')
    parser.add_argument('--manifest', default='test_vln_unseen.json')
    parser.add_argument('--base-env', default='base')
    parser.add_argument('--habitat-env', default='habitat')
    parser.add_argument('--limit', type=int, default=0, help='Only run first N episodes, 0 means all')
    parser.add_argument('--start-index', type=int, default=1, help='1-based episode start index')
    parser.add_argument('--fps', type=int, default=6)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    manifest_path = (repo_root / args.manifest).resolve() if not os.path.isabs(args.manifest) else Path(args.manifest).resolve()
    result_root = (repo_root / args.result_dir).resolve() if not os.path.isabs(args.result_dir) else Path(args.result_dir).resolve()
    shared_folder = repo_root / 'shared_folder'
    without_screenshot_root = repo_root / 'without_screenshot'
    conda_sh = Path('/root/miniconda3/etc/profile.d/conda.sh')
    model_script = repo_root / 'online_eval' / 'vln_eval' / 'model_runner.py'
    sim_script = repo_root / 'online_eval' / 'vln_eval' / 'sim_runnner.py'
    controller_script = repo_root / 'online_eval' / 'vln_eval' / 'vln_controller.py'
    active_manifest_path = repo_root / 'test_vln_unseen.json'

    result_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime('unseen_eval_v2_%Y%m%d_%H%M%S')
    run_dir = result_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    episodes_dir = run_dir / 'episodes'
    logs_dir = run_dir / 'logs'
    episodes_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    manifest_backup = run_dir / 'manifest_used.json'
    shutil.copy2(manifest_path, manifest_backup)

    original_active_manifest_backup = run_dir / 'original_test_vln_unseen.json'
    if active_manifest_path.exists():
        shutil.copy2(active_manifest_path, original_active_manifest_backup)

    with manifest_path.open('r', encoding='utf-8') as f:
        all_manifest = json.load(f)

    all_items = list(all_manifest.items())
    start_idx = max(args.start_index - 1, 0)
    all_items = all_items[start_idx:]
    if args.limit > 0:
        all_items = all_items[:args.limit]

    total = len(all_items)
    if total == 0:
        raise ValueError('没有可运行的 episode')

    summary = []
    temp_manifest = run_dir / 'current_episode_manifest.json'

    try:
        for local_idx, (episode_key, instructions) in enumerate(all_items, start=1):
            remaining = total - local_idx
            print(f'\n[{local_idx}/{total}] 当前: {episode_key}')
            print(f'剩余: {remaining}')

            episode_dir = episodes_dir / f'{local_idx:04d}_{safe_episode_name(episode_key)}'
            episode_dir.mkdir(parents=True, exist_ok=True)

            ensure_empty_shared_folder(shared_folder)
            write_single_episode_manifest(temp_manifest, episode_key, instructions)
            shutil.copy2(temp_manifest, active_manifest_path)

            model_proc = sim_proc = controller_proc = None
            model_log = sim_log = controller_log = None
            error_message = None

            try:
                model_proc, model_log = start_service(
                    conda_sh, args.base_env, model_script, repo_root, logs_dir / f'{local_idx:04d}_model.log'
                )
                time.sleep(STARTUP_WAIT_SECONDS)

                sim_proc, sim_log = start_service(
                    conda_sh, args.habitat_env, sim_script, repo_root, logs_dir / f'{local_idx:04d}_sim.log'
                )
                time.sleep(2)

                controller_proc, controller_log = start_service(
                    conda_sh, args.habitat_env, controller_script, repo_root, logs_dir / f'{local_idx:04d}_controller.log'
                )

                wait_for_episode_result(shared_folder, episode_key, EPISODE_TIMEOUT_SECONDS)

            except Exception as e:
                error_message = str(e)
                print(f'episode 运行失败: {episode_key} -> {error_message}')

            finally:
                kill_process(controller_proc)
                kill_process(sim_proc)
                kill_process(model_proc)
                for log_file in [model_log, sim_log, controller_log]:
                    if log_file:
                        log_file.close()

            shared_backup_dir = episode_dir / 'shared_folder'
            backup_shared_folder(shared_folder, shared_backup_dir)

            trajectory_json = shared_backup_dir / 'trajectories' / f'{safe_episode_name(episode_key)}.json'
            video_path = export_video(shared_backup_dir / 'images', episode_dir / 'episode.mp4', fps=args.fps)

            action_trace_path = None
            metrics_path = None
            metrics = None
            traj_data = None

            if trajectory_json.exists():
                action_trace_path = build_action_trace(trajectory_json, episode_dir / 'interaction_actions.json')
                metrics = compute_vln_metrics(trajectory_json, without_screenshot_root)
                metrics_path = episode_dir / 'metrics.json'
                save_json(metrics, metrics_path)
                with trajectory_json.open('r', encoding='utf-8') as f:
                    traj_data = json.load(f)
            else:
                save_json({'episode_key': episode_key, 'error': error_message or 'trajectory file missing'}, episode_dir / 'error.json')

            summary.append({
                'index': local_idx,
                'episode_key': episode_key,
                'remaining': remaining,
                'steps': traj_data.get('steps') if traj_data else None,
                'termination_reason': traj_data.get('termination_reason') if traj_data else None,
                'success': traj_data.get('success') if traj_data else None,
                'video_path': str(video_path) if video_path else None,
                'action_trace_path': str(action_trace_path) if action_trace_path else None,
                'metrics_path': str(metrics_path) if metrics_path else None,
                'shared_backup_path': str(shared_backup_dir),
                'error': error_message,
                'metrics': metrics,
            })

            save_json(summary, run_dir / 'summary.partial.json')
            ensure_empty_shared_folder(shared_folder)

    finally:
        if original_active_manifest_backup.exists():
            shutil.copy2(original_active_manifest_backup, active_manifest_path)

    save_json(summary, run_dir / 'summary.json')

    valid_metrics = [item['metrics'] for item in summary if item.get('metrics')]
    valid = len(valid_metrics)
    overall = {
        'run_id': run_id,
        'manifest': str(manifest_path),
        'episodes_run': len(summary),
        'episodes_with_metrics': valid,
        'average_NE': sum(item['NE'] for item in valid_metrics) / valid if valid else 0.0,
        'success_rate': sum(item['SR'] for item in valid_metrics) / valid if valid else 0.0,
        'online_success_rate': sum(item['OSR'] for item in valid_metrics) / valid if valid else 0.0,
        'average_nDTW': sum(item['nDTW'] for item in valid_metrics) / valid if valid else 0.0,
        'summary_path': str(run_dir / 'summary.json'),
    }
    save_json(overall, run_dir / 'overall_metrics.json')

    print('\n全部 unseen eval v2 完成')
    print(json.dumps(overall, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

