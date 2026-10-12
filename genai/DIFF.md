---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0 (OpenAIInstrumentor), opentelemetry-sdk 1.45.0, openai 3.19.2, exported with opentelemetry-exporter-otlp-json-file 0.66b0"
  spec_ref: "semantic-conventions@v1.41.1"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.temperature, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.top_p, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.conversation.id, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.output.type, emitted: false, in_spec: true, stability: development}
    - {name: gen_ai.system, emitted: false, in_spec: true, stability: deprecated}
---
<!-- ai-generated: 80% - Claude Code ran the call against a local Ollama (qwen3:0.6b) and compared the span with the v1.41.1 gen-ai registry; reviewed by the repository owner -->

# What the library emits, against the spec

One chat completion (`qwen3:0.6b` on a local Ollama, through its OpenAI-compatible `/v1` endpoint) was instrumented
with `OpenAIInstrumentor` and exported as OTLP JSON to `genai/spans.json`, by `genai/call.py`. The span carries ten
`gen_ai.*` attributes, and the registry of `semantic-conventions@v1.41.1` (`model/gen-ai/registry.yaml`) defines
every one of them, all at stability `development`.

**What agrees.** The library uses the current names throughout: `gen_ai.provider.name` rather than the deprecated
`gen_ai.system`, and `gen_ai.usage.input_tokens` / `output_tokens` rather than the deprecated `prompt_tokens` /
`completion_tokens`. The request parameters we set (`max_tokens`, `temperature`) are recorded, and the response
side (`id`, `model`, `finish_reasons`, both token counts) is complete for a non-streaming call.

**What it does not emit.** `gen_ai.request.top_p` is absent because we did not send one: the library records the
parameters of the request, not defaults. `gen_ai.conversation.id` and `gen_ai.output.type` are defined but not
derivable from a single stateless chat call. `gen_ai.system` is deliberately not emitted; v1.41.1 marks it
deprecated in favour of `gen_ai.provider.name`.

**What that means for a dashboard.** Everything is `development`: the names may still change between releases, so
a dashboard or an alert on token usage should pin the instrumentation version and expect a rename on upgrade.
`gen_ai.response.model` is worth a panel of its own: an OpenAI-compatible server may answer with a different model
than the one requested, and only the response attribute shows which one actually ran.
