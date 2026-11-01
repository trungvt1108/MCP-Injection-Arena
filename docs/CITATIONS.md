# Citations

MCP Injection Arena reuses attack templates from published prompt-injection
benchmarks so that defenses can be compared against established attack families
on the same scenarios. If you use these templates through the arena, please cite
the original work as well as the arena.

Each attack template registered in `arena.attacks.templates` records a `source`,
a `license`, and a `citation` key that matches an entry below. Persuasive payload
text from these suites is **not** vendored into this repository: the adapters in
`arena/attacks/templates/external.py` load it at run time from each suite's own
installed package, under that suite's license.

## Attack-suite licenses (as checked 2026-11-02)

| Suite | `citation` key | License (code) | Loaded how | Status |
|-------|----------------|----------------|------------|--------|
| AgentDojo | `debenedetti2024agentdojo` | MIT | at run time from the installed `agentdojo` package | enabled (verified vs. 0.1.35) |
| InjecAgent | `zhan2024injecagent` | unconfirmed — no `LICENSE` at the repo root | from a local clone, once verified | adapter pending (raises with instructions) |
| BIPIA | `yi2024bipia` | MIT (code); datasets have separate licenses | from a local clone, once verified | adapter pending (raises with instructions) |

Confirm each suite's license for its *attack text* before loading or
redistributing it. See `arena/attacks/templates/external.py` for the exact items
still to verify for InjecAgent and BIPIA.

## BibTeX

```bibtex
@inproceedings{debenedetti2024agentdojo,
  title     = {{AgentDojo}: A Dynamic Environment to Evaluate Attacks and Defenses for {LLM} Agents},
  author    = {Debenedetti, Edoardo and Zhang, Jie and Balunovi\'c, Mislav and
               Beurer-Kellner, Luca and Fischer, Marc and Tram\`er, Florian},
  booktitle = {Advances in Neural Information Processing Systems (NeurIPS)
               Datasets and Benchmarks Track},
  year      = {2024},
  eprint    = {2406.13352},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR}
}

@inproceedings{zhan2024injecagent,
  title     = {{InjecAgent}: Benchmarking Indirect Prompt Injections in
               Tool-Integrated Large Language Model Agents},
  author    = {Zhan, Qiusi and Liang, Zhixiang and Ying, Zifan and Kang, Daniel},
  booktitle = {Findings of the Association for Computational Linguistics (ACL)},
  year      = {2024},
  eprint    = {2403.02691},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR}
}

@inproceedings{yi2024bipia,
  title     = {Benchmarking and Defending Against Indirect Prompt Injection
               Attacks on Large Language Models},
  author    = {Yi, Jingwei and Xie, Yueqi and Zhu, Bin and Kiciman, Emre and
               Sun, Guangzhong and Xie, Xing and Wu, Fangzhao},
  booktitle = {Proceedings of the ACM SIGKDD Conference on Knowledge Discovery
               and Data Mining (KDD)},
  year      = {2025},
  eprint    = {2312.14197},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR}
}
```
