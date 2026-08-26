FROM python:3.12-slim

ENV PYTHONUTF8=1

RUN apt-get update && apt-get install -y \
    lua5.4 \
    luarocks \
    curl \
    && ln -sf /usr/bin/lua5.4 /usr/bin/lua \
    && ln -sf /usr/bin/luac5.4 /usr/bin/luac \
    && luarocks install luacheck \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --retries 10 --default-timeout 120 -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
