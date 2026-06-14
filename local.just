serve:
    uv run meowdb serve

dev:
    uv run meowdb serve --reload

ingest path:
    uv run meowdb ingest "{{path}}"

screenshots:
    cd ui && npm run test:screenshot

screenshots-post pr:
    bash scripts/post-screenshots.sh "{{pr}}" ui/screenshots
