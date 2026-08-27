#!/bin/sh
set -e

if [ -d .git ]; then
  git="git -c safe.directory=/backend"
  APP_REPO=$($git remote get-url origin 2>/dev/null | sed -e 's#^git@github.com:#https://github.com/#' -e 's#\.git$##')
  APP_BRANCH=$($git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
  APP_COMMIT=$($git rev-parse --short HEAD 2>/dev/null || true)
  export APP_REPO APP_BRANCH APP_COMMIT
fi

cd backend
alembic upgrade head
exec python -m app
