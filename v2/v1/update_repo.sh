#!/bin/bash
cd /home/brett/downtime
git add .
git commit -m "Auto-update: $(date)"
git push origin main
