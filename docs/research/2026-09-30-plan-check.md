# Plan check, 2026-09-30

Two read-only review agents (Sonnet, with web lookups) fact-checked the first draft of the
design before it was approved. This records what they found and what changed in
[the spec](../specs/2026-09-30-degreepilot-design.md). Sources are the ones they cited.

## Training on free Kaggle GPUs

| Claim | Verdict | What changed | Source |
|---|---|---|---|
| ~30 GPU-hours/week, shared by P100 and T4×2 | Confirmed | — | [Kaggle GPU docs](https://www.kaggle.com/docs/efficient-gpu-usage) |
| Pushed runs can use T4×2 | Confirmed, if pinned | `"machine_shape": "NvidiaTeslaT4"`. Unpinned runs can land on a P100, which current PyTorch can't run (sm_60 dropped). The script asserts compute capability (7, 5). | [kernel metadata](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md) |
| GPU sessions last 12 h | Uncertain (an older page says 9 h) | Stop time is a parameter, default 11.5 h; checkpoints every 30 min cap the loss | [Ultralytics on Kaggle](https://docs.ultralytics.com/integrations/kaggle) |
| CPU sessions don't use GPU quota | Confirmed | Tokenizing runs in CPU sessions | [Kaggle notebooks](https://www.kaggle.com/docs/notebooks) |
| Internet needs phone verification | Confirmed | `enable_internet: true` in metadata | [Kaggle forum](https://www.kaggle.com/product-feedback/63544) |
| A run can publish a dataset version for the next run | Uncertain | Tested in the probe; fallback is two alternating kernels via `kernel_sources` | [Kaggle notebooks](https://www.kaggle.com/docs/notebooks) |
| `/kaggle/working` keeps output | Confirmed, up to 20 GB | Keep 2 checkpoints | [Kaggle notebooks](https://www.kaggle.com/docs/notebooks) |
| Kaggle's PyTorch runs fp16 AMP on T4 | Confirmed (sm_70 and up) | fp16 + GradScaler; T4 has no bf16 | [docker-python #1546](https://github.com/Kaggle/docker-python/issues/1546) |
| SDPA on T4 | Flash needs sm80+; the memory-efficient backend works | Noted | [PyTorch SDPA tutorial](https://docs.pytorch.org/tutorials/intermediate/scaled_dot_product_attention_tutorial.html) |
| `torch.compile` on T4 | Uncertain | Behind a flag, benchmarked in the probe | [torch.compiler docs](https://docs.pytorch.org/docs/stable/torch.compiler.html) |
| `torchrun` DDP in a notebook | Uncertain | Launched as a subprocess from a script kernel; `NCCL_P2P_DISABLE=1` if it hangs | [PyTorch forum](https://discuss.pytorch.org/t/help-with-ddp-in-kaggle-notebook/213369) |
| 2×T4 trains ~2.2B tokens in 20–30 h | **Wrong, about 2× optimistic** | Estimate now 14–22k tokens/s: 28–45 h for 110M. `dp-60m` trains first (~9–13 h) | [nanoGPT on T4](https://16x.engineer/2023/12/29/nanoGPT-azure-T4-ubuntu-guide.html) |
| FineWeb-Edu `sample/10BT` downloads anonymously | Confirmed: 14 parquet files, ~2.15 GB and ~0.7B tokens each, ODC-By | 2 files for `dp-60m`; download → tokenize → delete | [file list](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu/tree/main/sample/10BT) |
| tiktoken accepts custom merge ranks | Confirmed | Not used: our own cached encoder is fast enough | [tiktoken](https://github.com/openai/tiktoken#extending-tiktoken) |
| O*NET license and contents | Confirmed: release 31.0, CC BY 4.0. Skills and Knowledge carry importance + level; task importance is in Task Ratings; Technology Skills have flags only | Spec updated | [O*NET database](https://www.onetcenter.org/database.html) |
| CIP 2020 ↔ SOC 2018 crosswalk | Confirmed: NCES Excel file, many-to-many, federal work | — | [NCES CIP resources](https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56) |

## Browser runtime and hosting

| Claim | Verdict | What changed | Source |
|---|---|---|---|
| ONNX Runtime Web runs quantized MatMul on WebGPU | Confirmed via `MatMulNBits` (4-bit, 8-bit where supported); plain int8 `MatMulInteger` is poorly covered | Export as `MatMulNBits` | [ORT 1.30](https://github.com/microsoft/onnxruntime/releases/tag/v1.30.0) |
| A `torch.onnx` GPT with KV cache runs well on WebGPU | Uncertain: unsupported ops fall back to CPU | Phase 2 browser spike with `dp-10m`, before any GPU time | [ORT WebGPU EP](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html) |
| WASM fallback exists | Confirmed | Kept | [ORT perf diagnosis](https://onnxruntime.ai/docs/tutorials/web/performance-diagnosis.html) |
| WebGPU availability | Chrome/Edge 113+ on Windows (incl. Intel Gen12), Safari 26 on macOS/iOS, Firefox 141+ on Windows | WASM covers the rest | [web.dev](https://web.dev/blog/webgpu-supported-major-browsers) |
| A ~110M model is fast on an integrated GPU | Uncertain: SmolLM-135M ran ~20 tok/s on an Intel GPU, while multithreaded CPU ran ~93 tok/s | Measure WebGPU vs WASM threads; COOP/COEP headers; stream rows as they generate | [yzma #404](https://github.com/hybridgroup/yzma/pull/404) |
| Best $0 host | Cloudflare Pages: 25 MiB/file, no bandwidth cap, commercial use OK. Vercel Hobby is non-commercial; GitHub Pages bans SaaS | Cloudflare Pages | [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) |

## Premortem: it failed six months later. Why?

1. **PDF text path undefined.** Fix: pdf.js in the browser and in Node for training and test
   text; scanned PDFs get a paste fallback.
2. **Eval bars too strict and too noisy.** Fix: field-level F1, at least 100 real rows per
   family, confidence intervals; J3 as template + model rewording counts as success.
3. **The loop was missing inputs.** Fix: interests check (RIASEC), "not for me", weekly check-in.
4. **Students outside the US.** Fix: field-of-study picker; Canadian occupation data (OaSIS)
   to evaluate; French later.
5. **Compute schedule.** Fix: `dp-60m` first, `dp-110m` only if a job needs it, browser spike
   before any GPU time.
6. **Storage and trust.** Fix: profile export/import, `navigator.storage.persist()`, O*NET
   attribution, J3 text shown beside the raw facts.
