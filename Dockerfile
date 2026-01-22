FROM vllm/vllm-openai:v0.11.0

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "/model", "--host", "0.0.0.0", "--port", "8000"]
