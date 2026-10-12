# ai-generated: 85% - Claude Code wrote this one-off script for Lab 3 Stretch 1 (M-28); run once, its output is genai/spans.json
"""One instrumented LLM call, exported as OTLP JSON to genai/spans.json.

Run from the repository root (needs an OpenAI-compatible endpoint, here a local Ollama):
    pip install openai==3.19.2 opentelemetry-sdk==1.45.0 \
        opentelemetry-instrumentation-genai-openai==1.2b0 opentelemetry-exporter-otlp-json-file==0.66b0
    OPENAI_BASE_URL=http://localhost:11434/v1 python genai/call.py
"""

import os
from pathlib import Path

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

OUT = Path(__file__).with_name("spans.json")
MODEL = os.environ.get("GENAI_MODEL", "qwen3:0.6b")

OUT.unlink(missing_ok=True)
provider = TracerProvider(resource=Resource.create({"service.name": "svcdesk-genai-diff"}))
provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(OUT)))
trace.set_tracer_provider(provider)
OpenAIInstrumentor().instrument(tracer_provider=provider)

client = OpenAI(base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"), api_key="ollama")
reply = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "In one sentence: what is a known error in ITIL problem management?"}],
    max_tokens=80,
    temperature=0.2,
)
print(reply.choices[0].message.content)
provider.shutdown()
print(f"spans written to {OUT}")
