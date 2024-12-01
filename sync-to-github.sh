#!/bin/bash
cd /home/brett/downtime
git add .
git commit -m "Automated sync: $(date)"
git push origin main
