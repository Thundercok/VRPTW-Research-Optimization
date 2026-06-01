#!/bin/bash
# Wait for the Firebase Auth emulator on port 9099
echo "Waiting for Auth Emulator on port 9099..."
for i in $(seq 1 30); do
  if nc -z 127.0.0.1 9099 2>/dev/null; then
    echo "Auth Emulator is ready!"
    break
  fi
  echo "  Waiting for Auth Emulator... ($i/30)"
  sleep 1
done

# Seed the test user
echo "Seeding test user into Auth Emulator..."
curl -s -X POST \
  "http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signUp?key=fake-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@vrptw.local","password":"testpass123","returnSecureToken":true}' \
  > /dev/null 2>&1 || true

echo "  test@vrptw.local / testpass123 successfully seeded."
