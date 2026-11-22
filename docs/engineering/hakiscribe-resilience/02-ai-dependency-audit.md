# 02 — AI dependency audit

Every external AI touchpoint that Local-Only / Private must control. Frontier paths stay intact in `cloud` and hybrid cloud-routed tasks.

## ASR / speech

| Provider | Role | Path |
| --- | --- | --- |
| OpenRouter Whisper | Default live captions | `transcription.py` `OpenRouterWhisperProvider` |
| OpenAI Whisper | Optional ASR | `OpenAIWhisperProvider` |
| Groq Whisper | Optional ASR | `GroqWhisperProvider` |
| Intron Sahara | Code-switch refine + court hearing | `IntronVoiceProvider`, finalize in `sessions.py` |
| NVIDIA NIM ASR | Self-hosted | `NvidiaNimWhisperProvider`, `nvidia_nim.py` |
| Omi device | Pre-transcribed segments | `omi_webhook.py` |

## LLM / detect / draft / Ask

| Provider | Role | Path |
| --- | --- | --- |
| Nebius Nemotron | Preferred detect/draft/research | `nebius.py`, connectors |
| OpenRouter | Default fallback LLM | `llm_client.py`, `generation.py`, `action_detector.py` |
| Anthropic | Ask connector | `integrations.py`, `chat.py` |
| OpenAI | Ask + optional ASR | same |
| Gemini / Vertex | Ask | `oauth.py` `gemini_oauth`, `chat.py` |
| Groq / Mistral | Ask | `integrations.py` |
| `claude_custom` | Any OpenAI-compatible base URL | `integrations.py` |
| NVIDIA NIM LLM | Self-hosted | `nvidia_nim.py` |

## Research (not transcript evidence)

| Provider | Path |
| --- | --- |
| Tavily | `tavily.py` |
| Exa | `exa_client.py`, frontend `/research` |

## Orchestration

| System | Notes |
| --- | --- |
| Trigger.dev | Relays detect/generate/research to FastAPI `/internal/*`; cloud SaaS |
| In-process fallback | Used when `TRIGGER_SECRET_KEY` unset; preferred for `local_only` |

## Env keys (non-exhaustive)

`ASR_PROVIDER`, `ASR_MODEL`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `INTRON_API_KEY`, `LLM_PROVIDER`, `NEBIUS_*`, `NVIDIA_NIM_*`, `TAVILY_API_KEY`, `EXA_API_KEY`, `DETECTION_MODEL`, `DRAFTING_MODEL`, `ASK_MODEL`, plus Stage A: `HAKISCRIBE_AI_MODE`, `HAKISCRIBE_ROUTE_*`, `LOCAL_WHISPER_*`, `OLLAMA_*`.

## Not present before Stage A

Local Whisper, Ollama, Docker Compose inference, dedicated diarization, Local-Only network boundary, hybrid route matrix.
