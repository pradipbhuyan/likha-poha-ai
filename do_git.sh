#!/bin/bash
cd /Users/a0247716/Pradips_Project/cbse-tutor-platform
echo "=== GIT STATUS ===" > /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt
git status --short >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt 2>&1
echo "=== LOG ===" >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt
git log --oneline -3 >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt 2>&1
echo "=== ADD ===" >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt
git add -A >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt 2>&1
echo "=== COMMIT ===" >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt
git commit -m "feat: Session recovery — all changes from 22 Jun 2026" >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt 2>&1
echo "=== PUSH ===" >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt
git push origin main >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt 2>&1
echo "DONE" >> /Users/a0247716/Pradips_Project/cbse-tutor-platform/git_out.txt
