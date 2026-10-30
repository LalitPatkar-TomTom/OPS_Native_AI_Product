# OPS Native AI trigger engine — runs as an Azure Container Apps job next to OPS Hub.
# Build: az acr build -r tomtomopshub -t ops-native-ai:<tag> .
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Kolkata \
    OPS_OUTPUT_DIR=/work/output \
    OPS_DATA_DIR=/data/config/native-ai \
    OPS_SKILLS_SHARE=/data/skills

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY azure/requirements-azure.txt /tmp/requirements-azure.txt
RUN pip install --no-cache-dir -r /tmp/requirements-azure.txt

COPY MultiAgent_Briefing /app/MultiAgent_Briefing
COPY ["AI Architecture/skills/Personal Skills", "/app/AI Architecture/skills/Personal Skills"]
COPY azure /app/azure
COPY comms /app/comms
RUN sed -i 's/\r$//' /app/azure/entrypoint.sh && chmod +x /app/azure/entrypoint.sh

# Default: a scheduled run. Manual runs pass other fire_all_now.py arguments, e.g. --uc UC1
ENTRYPOINT ["/app/azure/entrypoint.sh"]
CMD ["--scheduled"]
