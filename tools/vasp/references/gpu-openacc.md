# VASP on GPUs (OpenACC builds)

> Load this when: running VASP on GPU nodes — choosing between CPU and GPU builds, writing the launch script, setting ranks/threads per GPU, or adapting INCAR parallelization for OpenACC VASP. For generic Slurm GPU discovery and request syntax, also load `tools/hpc-submit/references/running.md`.

## Build choice is a method decision

Do not submit a CPU-only VASP MPI build to a GPU partition. For GPU nodes, use the site's OpenACC/GPU VASP module and launcher (record them in the private cluster guide, under its VASP/GPU section). If strict method reproduction requires a specific CPU VASP version that is unavailable as a GPU build, treat the CPU-vs-GPU choice as a method/runtime decision and ask before changing versions.

## Binary choice

- `vasp_std` for general k-meshes.
- `vasp_gam` for true Gamma-only jobs (molecules in boxes, large supercells with `1 1 1` Gamma KPOINTS) — often faster.
- `vasp_ncl` for SOC/noncollinear, if the GPU build provides it.

## Launch template — one MPI rank per GPU

All bracketed values come from the cluster guide; never hardcode partition, module, or GPU-type names in committed files.

```bash
#!/bin/bash
#SBATCH --job-name=vasp-gpu
#SBATCH --partition=<gpu-partition>
#SBATCH --nodes=1
#SBATCH --gres=gpu:<type>:4           # typed GRES if the cluster has it; else the site's --gpus form
#SBATCH --ntasks-per-node=4           # one MPI rank per GPU
#SBATCH --cpus-per-task=<cores-per-gpu>
#SBATCH --gpu-bind=none               # avoid hiding peer GPUs from GPU-aware MPI/NCCL
#SBATCH --time=24:00:00
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

[[ "${1:-}" != "--dry-run" ]] || { echo "Use: sbatch --test-only $0"; exit 0; }
[[ -n "${SLURM_JOB_ID:-}" ]] || { echo "ERROR: use: sbatch $0" >&2; exit 2; }

module purge
module load <vasp-openacc-module>
ulimit -s unlimited

cd "$SLURM_SUBMIT_DIR"

NGPU=${SLURM_NTASKS:-${SLURM_GPUS:-${SLURM_GPUS_ON_NODE:-4}}}
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-<cores-per-gpu>}
export OMP_PLACES=cores
export OMP_PROC_BIND=close
export OMP_STACKSIZE=512m
export OMP_WAIT_POLICY=PASSIVE

# Balance ranks across CPU sockets. This assumes 2 sockets per node
# (1 GPU -> 1/socket, 4 -> 2/socket, 8 -> 4/socket); tune to local hardware.
RPS=$(( (NGPU + 1) / 2 ))
BIN=vasp_std                          # vasp_gam for Gamma-only; vasp_ncl for SOC if supported

mpirun -np "$NGPU" --map-by ppr:${RPS}:socket:PE=${OMP_NUM_THREADS} --bind-to core \
  -x OMP_NUM_THREADS -x OMP_PLACES -x OMP_PROC_BIND -x OMP_STACKSIZE -x OMP_WAIT_POLICY \
  "$BIN"
```

If the site's documented policy says not to set `--ntasks`, `--cpus-per-task`, or `--mem` for GPU jobs, respect that — some clusters derive CPU/memory allocation from the GPU request, and conflicting directives cause rejection or bad placement. If the site uses typed GRES without auto-derived CPU allocation, set `--ntasks-per-node=<GPUs>` and `--cpus-per-task=<cores per GPU>` explicitly so ranks and threads match the GPU count.

## Practical rules

- Keep MPI ranks equal to GPU count. Do not run tens of CPU-style MPI ranks on a GPU VASP job.
- Do not carry CPU INCAR parallel settings over. `NCORE`, `KPAR`, and `NPAR` choices
  that helped CPU jobs can hurt or fail GPU jobs. Local default is to omit `NPAR` and
  `NCORE` for GPU/OpenACC inputs unless the GPU module documentation explicitly
  recommends them; then benchmark.
- NEB on GPUs works best with one image per GPU; keep total GPUs/ranks divisible by `IMAGES`.
- Check early stdout/stderr for CUDA/OpenACC/MPI binding errors before letting a long job run.
- Record GPU partition, GPU count/type, module, binary, and the exact launch command with each run.
