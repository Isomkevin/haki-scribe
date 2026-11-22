FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-diarization.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Diarization pulls torch + pyannote (~2 GB). Opt in with
#   docker compose build --build-arg WITH_DIARIZATION=1 faster-whisper
ARG WITH_DIARIZATION=0
RUN if [ "$WITH_DIARIZATION" = "1" ]; then pip install --no-cache-dir -r requirements-diarization.txt; fi

COPY server.py diarize.py ./

ENV WHISPER_MODEL=Systran/faster-whisper-large-v3
ENV WHISPER_DEVICE=cpu
ENV WHISPER_COMPUTE_TYPE=int8
EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
