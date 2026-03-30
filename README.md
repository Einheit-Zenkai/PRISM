# Project Title: PRISM — Probabilistic Real-time Intelligent Scheduling Mechanism

## Overview
A research simulation comparing traditional OS scheduling algorithms against a hybrid intelligent scheduler that uses probabilistic pre-analysis and machine learning to minimize context switching overhead.

## Problem Statement
Traditional schedulers like Round Robin are reactive — they make no predictions about process behavior before execution. This causes unnecessary context switches, cache misses, and higher turnaround times. PRISM addresses this by analyzing processes before scheduling them.

## Proposed Solution
A three-layer hybrid framework:
- Layer 1: Probabilistic pre-analysis using Markov Chains and Poisson arrival rates
- Layer 2: ML classification using Random Forest (CPU-bound vs I/O-bound vs Mixed)
- Layer 3: Deep Learning prediction using LSTM for burst sequence forecasting
- Online learning feedback loop that improves predictions over time

## Algorithms Compared (Baselines)
- FCFS (First Come First Serve)
- SJF (Shortest Job First)
- Round Robin (quantum = 4ms)
- Priority Scheduling
- PRISM (our proposed scheduler)

## Evaluation Metrics
- Average Turnaround Time (ms)
- Average Waiting Time (ms)
- Context Switch Count
- CPU Utilization (%)
- Jain's Fairness Index

## Tech Stack
- Python 3.x
- SimPy (discrete event simulation)
- NumPy (numerical computation)
- Scikit-learn (Random Forest classifier)
- Matplotlib (result visualization)

## Project Structure
- `main.py`: Entry point and simulation runner
- `requirements.txt`: Dependencies
- `results/`: Output graphs and CSVs

## How to Run
- Create virtual environment: `python -m venv venv`
- Activate: `venv\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt`
- Run simulation: `python main.py`

## Research Paper
This simulation supports the paper "PRISM: A Probabilistic Real-time Intelligent Scheduling Mechanism for Minimizing Context Switch Overhead in Operating Systems". Target venue: IEEE ICCA / ICCCS.
