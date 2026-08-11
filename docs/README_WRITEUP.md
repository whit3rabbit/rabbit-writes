# What makes a README work: an evidence-based study

This is the research behind the `readme-writing` skill in this plugin. Rather than guess at "best practices," we pulled the README of 100 real, currently-trending GitHub repositories, measured their structure and prose mechanically, and read the most-starred ones by hand for the qualitative patterns a word-count can't see. Every claim below traces back to a number in `readme-analysis/` or a quoted line from a specific repo — nothing here is asserted from priors.

## Methodology

**Population.** The brief was "top 1,000 repos by stars gained in the past year." That query doesn't exist as a direct GitHub API call — GitHub's Search API has no "stars gained in window X" sort, and this session's network access to `api.github.com` and `github.com` is scoped to this repo only, so the Search API wasn't reachable at all. Two workarounds got us real data instead of a guess:

- **OSS Insight** (`api.ossinsight.io`), a public analytics API built on the GH Archive event stream, publishes a "Fastest Growing Repositories" ranking. Its finest trailing window is `past_3_months` — there's no `past_1_year` option — and it returns a fixed 100 rows. We used this as the population: real, measured quarterly star growth, not a total-stars leaderboard and not an estimate.
- Each candidate's authoritative metadata (total stars, creation date, default branch) came from **ungh.cc**, a public GitHub API mirror unaffected by the repo-scoping restriction, cross-checked against `img.shields.io` badge counts for a couple of spot samples (matched exactly).
- Every README was pulled verbatim from **raw.githubusercontent.com** (a static CDN, also unrestricted), trying the repo's default branch first and falling back through common filename casings.

The practical effect: this is a "top 100 by trailing-quarter star growth," not "top 1,000 by trailing-year star growth." We're naming that gap plainly rather than papering over it — 100 real, currently-relevant, momentum-having repos beat 1,000 the query couldn't actually produce. It also means the sample skews toward what's growing fast in mid-2026: a lot of AI-agent tooling, Claude/Codex "skill" packs, and dev-tool CLIs. That's a real bias worth knowing about before generalizing these findings to, say, a Python data-science library or a corporate SDK.

**Analysis.** A Python script (`scripts/03_analyze_readme.py`) parses each README with regex-based heuristics — not a full Markdown AST — to extract heading structure, sentence and paragraph length (code blocks and tables excluded from prose stats), image/badge counts, link style, and section word counts. Headings are mapped to 21 canonical categories (installation, features, license, etc.) by keyword match; anything that doesn't match a keyword is bucketed as "other" and excluded from the layout stats. This is a heuristic, not a certified parser — spot-checks against several READMEs by hand confirmed it gets the shape right, but exact counts (especially sentence splitting around abbreviations and version numbers) will be off by a few percent here and there.

**Correction, 9 August 2026.** The first pass of this study measured two things wrong, both for the same reason: the parser understood Markdown syntax and ignored HTML, in a corpus where 76% of READMEs use a raw-HTML header block.

- *Bare URLs.* The regex matched URLs inside HTML `href`/`src` attributes and inside inline code spans and counted them as unwrapped. 2,009 of the 2,357 "bare" URLs were attribute values in perfectly ordinary `<a>` and `<img>` tags. Corrected, bare URLs are **3.0%** of links, not 29.3%, and 50% of repos contain one, not 90%.
- *Badges and images.* Only Markdown `![]()` images were counted, so the badge row in a centered HTML header was invisible. Corrected, the median README carries **5** badges, not zero, and 80% carry at least one.

The section-order, length, and sentence statistics are unaffected: those never touched image or link syntax. Everything below is regenerated from the corrected scripts, and `scripts/readme-research/03_analyze_readme.py` now strips wrapped URLs before looking for bare ones. The lesson generalizes past this study: a Markdown-only parser measures a Markdown-only subset of a corpus that is half HTML, and it fails silently rather than loudly.

Twenty of the highest-star repos additionally got a hand-read qualitative pass — four batches of five, each read closely for structure, tone, and technique, with real quotes pulled rather than paraphrased. Those are cited by name throughout this document; the other 80 repos only have the quantitative pass.

## The population

Ranked by measured stars gained in the trailing 3 months (OSS Insight's `total_score`, which is real event-derived growth, not total popularity — a repo can have huge lifetime stars but modest recent growth if its viral moment was 6 months ago rather than 2). Full per-repo data — the raw README, computed stats, and (for the top 20) a qualitative note — lives in `readme-analysis/repos/<owner>__<repo>/`.

| Rank | Repo | Stars (total) | Stars gained (trailing 3mo) | Language | Data |
|---:|---|---:|---:|---|---|
| 1 | [mattpocock/skills](https://github.com/mattpocock/skills) | 211,274 | 4,905 | Shell | [data](readme-analysis/repos/mattpocock__skills/) |
| 2 | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | 227,968 | 4,042 | Python | [data](readme-analysis/repos/NousResearch__hermes-agent/) |
| 3 | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | 65,586 | 3,401 | C | [data](readme-analysis/repos/colbymchenry__codegraph/) |
| 4 | [obra/superpowers](https://github.com/obra/superpowers) | 269,760 | 3,348 | Shell | [data](readme-analysis/repos/obra__superpowers/) |
| 5 | [Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) | 78,591 | 3,324 | TypeScript | [data](readme-analysis/repos/Egonex-AI__Understand-Anything/) |
| 6 | [affaan-m/ECC](https://github.com/affaan-m/ECC) | 239,034 | 2,992 | JavaScript | [data](readme-analysis/repos/affaan-m__ECC/) |
| 7 | [pewdiepie-archdaemon/odysseus](https://github.com/pewdiepie-archdaemon/odysseus) | 85,057 | 2,689 | Python | [data](readme-analysis/repos/pewdiepie-archdaemon__odysseus/) |
| 8 | [farion1231/cc-switch](https://github.com/farion1231/cc-switch) | 125,965 | 2,608 | Rust | [data](readme-analysis/repos/farion1231__cc-switch/) |
| 9 | [tinyhumansai/openhuman](https://github.com/tinyhumansai/openhuman) | 36,134 | 2,377 | Rust | [data](readme-analysis/repos/tinyhumansai__openhuman/) |
| 10 | [nexu-io/open-design](https://github.com/nexu-io/open-design) | 84,750 | 2,366 | TypeScript | [data](readme-analysis/repos/nexu-io__open-design/) |
| 11 | [rohitg00/ai-engineering-from-scratch](https://github.com/rohitg00/ai-engineering-from-scratch) | 46,385 | 1,959 | Python | [data](readme-analysis/repos/rohitg00__ai-engineering-from-scratch/) |
| 12 | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | 99,405 | 1,833 | JavaScript | [data](readme-analysis/repos/DietrichGebert__ponytail/) |
| 13 | [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | 41,504 | 1,816 | Python | [data](readme-analysis/repos/Imbad0202__academic-research-skills/) |
| 14 | [CloakHQ/CloakBrowser](https://github.com/CloakHQ/CloakBrowser) | 29,802 | 1,813 | Python | [data](readme-analysis/repos/CloakHQ__CloakBrowser/) |
| 15 | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | 85,187 | 1,799 | JavaScript | [data](readme-analysis/repos/addyosmani__agent-skills/) |
| 16 | [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) | 65,660 | 1,731 | Python | [data](readme-analysis/repos/headroomlabs-ai__headroom/) |
| 17 | [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | 104,641 | 1,693 | Python | [data](readme-analysis/repos/Graphify-Labs__graphify/) |
| 18 | [github/spec-kit](https://github.com/github/spec-kit) | 125,998 | 1,610 | Python | [data](readme-analysis/repos/github__spec-kit/) |
| 19 | [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | 140,809 | 1,595 | Shell | [data](readme-analysis/repos/msitarzewski__agency-agents/) |
| 20 | [ruvnet/RuView](https://github.com/ruvnet/RuView) | 89,099 | 1,567 | Rust | [data](readme-analysis/repos/ruvnet__RuView/) |
| 21 | [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) | 26,793 | 1,555 | TypeScript | [data](readme-analysis/repos/rohitg00__agentmemory/) |
| 22 | [garrytan/gstack](https://github.com/garrytan/gstack) | 127,208 | 1,554 | TypeScript | [data](readme-analysis/repos/garrytan__gstack/) |
| 23 | [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) | 107,466 | 1,501 | — | [data](readme-analysis/repos/VoltAgent__awesome-design-md/) |
| 24 | [anthropics/financial-services](https://github.com/anthropics/financial-services) | 34,147 | 1,415 | Python | [data](readme-analysis/repos/anthropics__financial-services/) |
| 25 | [microsoft/markitdown](https://github.com/microsoft/markitdown) | 172,653 | 1,413 | Python | [data](readme-analysis/repos/microsoft__markitdown/) |
| 26 | [Hmbown/CodeWhale](https://github.com/Hmbown/CodeWhale) | 40,610 | 1,408 | Rust | [data](readme-analysis/repos/Hmbown__CodeWhale/) |
| 27 | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | 97,084 | 1,296 | JavaScript | [data](readme-analysis/repos/JuliusBrussee__caveman/) |
| 28 | [esengine/DeepSeek-Reasonix](https://github.com/esengine/DeepSeek-Reasonix) | 33,481 | 1,280 | Go | [data](readme-analysis/repos/esengine__DeepSeek-Reasonix/) |
| 29 | [earendil-works/pi](https://github.com/earendil-works/pi) | 86,066 | 1,265 | TypeScript | [data](readme-analysis/repos/earendil-works__pi/) |
| 30 | [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | 102,345 | 1,246 | Python | [data](readme-analysis/repos/harry0703__MoneyPrinterTurbo/) |
| 31 | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 115,036 | 1,242 | Python | [data](readme-analysis/repos/nextlevelbuilder__ui-ux-pro-max-skill/) |
| 32 | [antirez/ds4](https://github.com/antirez/ds4) | 21,061 | 1,226 | C | [data](readme-analysis/repos/antirez__ds4/) |
| 33 | [datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents) | 71,848 | 1,190 | Python | [data](readme-analysis/repos/datawhalechina__hello-agents/) |
| 34 | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | 69,777 | 1,158 | Python | [data](readme-analysis/repos/Panniantong__Agent-Reach/) |
| 35 | [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | 34,265 | 1,157 | Python | [data](readme-analysis/repos/Yuan1z0825__nature-skills/) |
| 36 | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | 96,872 | 1,156 | Python | [data](readme-analysis/repos/TauricResearch__TradingAgents/) |
| 37 | [rtk-ai/rtk](https://github.com/rtk-ai/rtk) | 75,375 | 1,142 | Rust | [data](readme-analysis/repos/rtk-ai__rtk/) |
| 38 | [hugohe3/ppt-master](https://github.com/hugohe3/ppt-master) | 44,118 | 1,131 | Python | [data](readme-analysis/repos/hugohe3__ppt-master/) |
| 39 | [BigPizzaV3/CodexPlusPlus](https://github.com/BigPizzaV3/CodexPlusPlus) | 28,403 | 1,127 | Rust | [data](readme-analysis/repos/BigPizzaV3__CodexPlusPlus/) |
| 40 | [ruvnet/ruflo](https://github.com/ruvnet/ruflo) | 67,509 | 1,088 | TypeScript | [data](readme-analysis/repos/ruvnet__ruflo/) |
| 41 | [mvanhorn/last30days-skill](https://github.com/mvanhorn/last30days-skill) | 57,766 | 1,084 | Python | [data](readme-analysis/repos/mvanhorn__last30days-skill/) |
| 42 | [decolua/9router](https://github.com/decolua/9router) | 25,071 | 1,033 | JavaScript | [data](readme-analysis/repos/decolua__9router/) |
| 43 | [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | 73,296 | 1,029 | Python | [data](readme-analysis/repos/D4Vinci__Scrapling/) |
| 44 | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | 33,331 | 1,011 | Python | [data](readme-analysis/repos/anthropics__claude-plugins-official/) |
| 45 | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 40,268 | 885 | TypeScript | [data](readme-analysis/repos/heygen-com__hyperframes/) |
| 46 | [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) | 45,069 | 878 | Python | [data](readme-analysis/repos/Alishahryar1__free-claude-code/) |
| 47 | [yikart/AiToEarn](https://github.com/yikart/AiToEarn) | 24,952 | 872 | TypeScript | [data](readme-analysis/repos/yikart__AiToEarn/) |
| 48 | [floci-io/floci](https://github.com/floci-io/floci) | 19,289 | 852 | Java | [data](readme-analysis/repos/floci-io__floci/) |
| 49 | [datawhalechina/easy-vibe](https://github.com/datawhalechina/easy-vibe) | 18,832 | 846 | JavaScript | [data](readme-analysis/repos/datawhalechina__easy-vibe/) |
| 50 | [ZhuLinsen/daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) | 61,273 | 823 | Python | [data](readme-analysis/repos/ZhuLinsen__daily_stock_analysis/) |
| 51 | [multica-ai/multica](https://github.com/multica-ai/multica) | 44,956 | 809 | Go | [data](readme-analysis/repos/multica-ai__multica/) |
| 52 | [supertone-inc/supertonic](https://github.com/supertone-inc/supertonic) | 13,638 | 805 | Swift | [data](readme-analysis/repos/supertone-inc__supertonic/) |
| 53 | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 57,434 | 789 | JavaScript | [data](readme-analysis/repos/pbakaus__impeccable/) |
| 54 | [AIDC-AI/Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video) | 26,602 | 765 | Python | [data](readme-analysis/repos/AIDC-AI__Pixelle-Video/) |
| 55 | [fathah/hermes-desktop](https://github.com/fathah/hermes-desktop) | 13,810 | 740 | TypeScript | [data](readme-analysis/repos/fathah__hermes-desktop/) |
| 56 | [mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) | 27,519 | 724 | Python | [data](readme-analysis/repos/mukul975__Anthropic-Cybersecurity-Skills/) |
| 57 | [garrytan/gbrain](https://github.com/garrytan/gbrain) | 28,080 | 720 | TypeScript | [data](readme-analysis/repos/garrytan__gbrain/) |
| 58 | [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | 46,345 | 718 | Python | [data](readme-analysis/repos/calesthio__OpenMontage/) |
| 59 | [santifer/career-ops](https://github.com/santifer/career-ops) | 63,319 | 716 | JavaScript | [data](readme-analysis/repos/santifer__career-ops/) |
| 60 | [elder-plinius/CL4R1T4S](https://github.com/elder-plinius/CL4R1T4S) | 46,823 | 701 | — | [data](readme-analysis/repos/elder-plinius__CL4R1T4S/) |
| 61 | [anthropics/claude-for-legal](https://github.com/anthropics/claude-for-legal) | 9,066 | 698 | Python | [data](readme-analysis/repos/anthropics__claude-for-legal/) |
| 62 | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 33,064 | 679 | Python | [data](readme-analysis/repos/K-Dense-AI__scientific-agent-skills/) |
| 63 | [Anil-matcha/Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) | 25,962 | 677 | JavaScript | [data](readme-analysis/repos/Anil-matcha__Open-Generative-AI/) |
| 64 | [crynta/terax-ai](https://github.com/crynta/terax-ai) | 8,916 | 671 | TypeScript | [data](readme-analysis/repos/crynta__terax-ai/) |
| 65 | [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp) | 38,308 | 670 | C | [data](readme-analysis/repos/DeusData__codebase-memory-mcp/) |
| 66 | [tashfeenahmed/freellmapi](https://github.com/tashfeenahmed/freellmapi) | 18,186 | 668 | TypeScript | [data](readme-analysis/repos/tashfeenahmed__freellmapi/) |
| 67 | [can1357/oh-my-pi](https://github.com/can1357/oh-my-pi) | 23,327 | 654 | TypeScript | [data](readme-analysis/repos/can1357__oh-my-pi/) |
| 68 | [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | 23,601 | 650 | HTML | [data](readme-analysis/repos/op7418__guizang-ppt-skill/) |
| 69 | [jamiepine/voicebox](https://github.com/jamiepine/voicebox) | 49,902 | 648 | TypeScript | [data](readme-analysis/repos/jamiepine__voicebox/) |
| 70 | [Wei-Shaw/sub2api](https://github.com/Wei-Shaw/sub2api) | 36,404 | 647 | Go | [data](readme-analysis/repos/Wei-Shaw__sub2api/) |
| 71 | [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) | 46,819 | 642 | Python | [data](readme-analysis/repos/HKUDS__CLI-Anything/) |
| 72 | [RyanCodrai/turbovec](https://github.com/RyanCodrai/turbovec) | 14,700 | 632 | Rust | [data](readme-analysis/repos/RyanCodrai__turbovec/) |
| 73 | [bytedance/UI-TARS-desktop](https://github.com/bytedance/UI-TARS-desktop) | 38,534 | 625 | TypeScript | [data](readme-analysis/repos/bytedance__UI-TARS-desktop/) |
| 74 | [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) | 23,398 | 599 | Python | [data](readme-analysis/repos/anthropics__knowledge-work-plugins/) |
| 75 | [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM) | 35,139 | 575 | Python | [data](readme-analysis/repos/OpenBMB__VoxCPM/) |
| 76 | [apple/container](https://github.com/apple/container) | 48,805 | 573 | Swift | [data](readme-analysis/repos/apple__container/) |
| 77 | [HKUDS/Vibe-Trading](https://github.com/HKUDS/Vibe-Trading) | 30,467 | 570 | Python | [data](readme-analysis/repos/HKUDS__Vibe-Trading/) |
| 78 | [Fincept-Corporation/FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal) | 30,061 | 567 | C++ | [data](readme-analysis/repos/Fincept-Corporation__FinceptTerminal/) |
| 79 | [TencentCloud/TencentDB-Agent-Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory) | 18,827 | 554 | TypeScript | [data](readme-analysis/repos/TencentCloud__TencentDB-Agent-Memory/) |
| 80 | [QuantumNous/new-api](https://github.com/QuantumNous/new-api) | 44,750 | 551 | Go | [data](readme-analysis/repos/QuantumNous__new-api/) |
| 81 | [google/skills](https://github.com/google/skills) | 17,274 | 550 | Python | [data](readme-analysis/repos/google__skills/) |
| 82 | [herdrdev/herdr](https://github.com/herdrdev/herdr) | 26,477 | 534 | Rust | [data](readme-analysis/repos/herdrdev__herdr/) |
| 83 | [google-labs-code/design.md](https://github.com/google-labs-code/design.md) | 27,094 | 524 | TypeScript | [data](readme-analysis/repos/google-labs-code__design.md/) |
| 84 | [rmyndharis/OpenWA](https://github.com/rmyndharis/OpenWA) | 12,600 | 515 | TypeScript | [data](readme-analysis/repos/rmyndharis__OpenWA/) |
| 85 | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | 43,695 | 507 | JavaScript | [data](readme-analysis/repos/coreyhaines31__marketingskills/) |
| 86 | [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 48,822 | 503 | TypeScript | [data](readme-analysis/repos/ChromeDevTools__chrome-devtools-mcp/) |
| 87 | [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook) | 36,576 | 492 | TypeScript | [data](readme-analysis/repos/lfnovo__open-notebook/) |
| 88 | [alibaba/open-code-review](https://github.com/alibaba/open-code-review) | 19,832 | 490 | Go | [data](readme-analysis/repos/alibaba__open-code-review/) |
| 89 | [FULU-Foundation/OrcaSlicer-bambulab](https://github.com/FULU-Foundation/OrcaSlicer-bambulab) | 7,105 | 486 | C++ | [data](readme-analysis/repos/FULU-Foundation__OrcaSlicer-bambulab/) |
| 90 | [blader/humanizer](https://github.com/blader/humanizer) | 34,536 | 484 | Python | [data](readme-analysis/repos/blader__humanizer/) |
| 91 | [stablyai/orca](https://github.com/stablyai/orca) | 40,902 | 475 | TypeScript | [data](readme-analysis/repos/stablyai__orca/) |
| 92 | [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) | 17,158 | 473 | Python | [data](readme-analysis/repos/nesquena__hermes-webui/) |
| 93 | [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) | 44,334 | 403 | TypeScript | [data](readme-analysis/repos/diegosouzapw__OmniRoute/) |
| 94 | [phuryn/pm-skills](https://github.com/phuryn/pm-skills) | 25,028 | 399 | — | [data](readme-analysis/repos/phuryn__pm-skills/) |
| 95 | [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 19,478 | 395 | Python | [data](readme-analysis/repos/virgiliojr94__book-to-skill/) |
| 96 | [JCodesMore/ai-website-cloner-template](https://github.com/JCodesMore/ai-website-cloner-template) | 31,493 | 385 | TypeScript | [data](readme-analysis/repos/JCodesMore__ai-website-cloner-template/) |
| 97 | [XiaomiMiMo/MiMo-Code](https://github.com/XiaomiMiMo/MiMo-Code) | 12,699 | 385 | TypeScript | [data](readme-analysis/repos/XiaomiMiMo__MiMo-Code/) |
| 98 | [usestrix/strix](https://github.com/usestrix/strix) | 50,349 | 368 | Python | [data](readme-analysis/repos/usestrix__strix/) |
| 99 | [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) | 30,982 | 340 | TypeScript | [data](readme-analysis/repos/MadsLorentzen__ai-job-search/) |
| 100 | [k1tbyte/Wand-Enhancer](https://github.com/k1tbyte/Wand-Enhancer) | 16,192 | 146 | C# | [data](readme-analysis/repos/k1tbyte__Wand-Enhancer/) |

Qualitative notes with quotes exist for ranks 1–20 (linked above). Quantitative stats (`stats.json`) exist for all 100.

## Layout: what sections show up, and in what order

Presence rate is how many of the 100 READMEs contain a heading matching that category anywhere in the document. Position is the average location of that heading across the document's length (0.0 = very first heading, 1.0 = very last), among the repos that have it. Read the two together: a section can be common *and* early (installation), common but late (license), or rare but consistently placed when it appears (roadmap).

| Section | Present in | Avg. position | Median length when present |
|---|---:|---:|---:|
| Features / Why | 59% | 0.21 (early) | 137 words |
| Table of contents | 12% | 0.23 (early) | 58 words |
| Installation / Setup | 84% | 0.33 | 112 words |
| Demo / Screenshots | 24% | 0.38 | 49 words |
| Sponsors | 13% | 0.39 | 143 words |
| Architecture / How it works | 41% | 0.46 | 92 words |
| Usage | 24% | 0.46 | 36 words |
| API / Docs | 44% | 0.53 | 121 words |
| Examples | 13% | 0.53 | 8 words |
| Security | 16% | 0.54 | 151 words |
| Configuration | 33% | 0.56 | 135 words |
| Support / Community | 46% | 0.59 | 158 words |
| FAQ | 17% | 0.61 | 253 words |
| Testing | 14% | 0.66 | 53 words |
| Changelog | 32% | 0.71 | 60 words |
| Contributing | 52% | 0.77 | 50 words |
| Credits / Acknowledgments | 28% | 0.80 | 82 words |
| License | 72% | 0.93 (very late) | 13 words |

The shape that falls out of this is almost exactly the "why → how → what's under the hood → how to help → legal" arc conventional wisdom describes, and it's consistent enough across 100 independently-authored repos to call it a real convention rather than a coincidence: **pitch first (features/why), then the fastest path to running it (installation), then depth (architecture/API/config) for people still reading, then community mechanics (contributing/credits), then license dead last.** License sections are also the shortest thing in a README by a wide margin — a median of 13 words, because nearly everyone just states the license name and links the `LICENSE` file rather than restating its terms.

Two things worth flagging as *not* universal, contrary to some style guides: a table of contents under an explicit "Table of contents" heading appears in only 12% of these READMEs, and 32% once you also count an unlabelled navigation list of three or more anchor links (either way it shows up mainly on genuinely long docs — spec-kit, RuView, ECC). An explicit "Usage" section is present in just 24%, because a large share of these tools fold usage examples directly into installation as a single "get it running" flow instead of splitting the two.

## Sentence and paragraph craft

- **Sentence length:** across repos with enough prose to measure reliably (≥5 sentences), the average README's mean sentence length is **20.1 words**, but the median is a shorter **13.3 words** — a handful of dense, long-form technical repos (ECC, gstack, RuView) pull the average up. Within a typical README, sentence length is genuinely mixed rather than uniform: **38% of sentences are short (<10 words), 37% are medium (10–20), and 26% are long (>20)** — burst-y, not metronomic. That variation is itself a signal: the READMEs that read best (superpowers, caveman, ponytail) deliberately alternate a short punch sentence against a longer explanatory one, the same "uneven like speech" pattern this plugin's own `rabbit-writes` craft engine already teaches for prose in general.
- **Paragraph length:** short. The average paragraph across the corpus is **28.4 words** — two or three sentences, not blocks of text. READMEs get read in a scroll, not settled into like an essay, and the corpus reflects that.
- **Overall length:** the median README (prose only, excluding code blocks) is **1,846 words**; the 25th percentile is 1,311 and the 75th is 3,612. There's a long tail of very long READMEs (90th percentile: 6,040 words) driven by repos that fold their entire reference manual into `README.md` instead of linking out to `docs/` (ECC, RuView, agency-agents all do this, and it's flagged as a mild anti-pattern in the qualitative notes below — length that trades skimmability for being a single source of truth).

## Visual formatting

| Technique | Share of READMEs using it |
|---|---:|
| Any code block | 97% |
| Markdown table | 82% |
| Centered header block (`<p align="center">` / `<div align="center">`) | 76% |
| Bare (un-markdown-linked) URLs somewhere in the doc | 50% |
| Demo media of any kind (screenshot, GIF, video, or explicit demo section) | 89% |
| Any badge | 80% |
| Badge row specifically in the first 20 lines | 67% |
| A screenshot or logo image | 87% |
| An animated GIF | 14% |
| An embedded video (YouTube/Loom/asciinema/`<video>`) | 19% |

Centering the header block (logo, title, tagline, badge row) is close to a majority convention at 76% — enough that skipping it now reads as a deliberate, slightly terse choice (as with `pi` and `spec-kit`'s more document-like open) rather than an oversight. Badges go with that header: 80% of these READMEs carry at least one, 67% put a row of them in the first 20 lines, and the median count is **5** (mean 5.7, with a tail — ECC carries 17). Where badges appear, they cluster around a small set of purposes: **license (56 occurrences across the corpus), version or package registry (47), social proof / star count (39), chat/community (29, mostly Discord), and build/CI status (27)**, with documentation badges a distant sixth (4). Coverage and code-quality badges barely register — much rarer here than in a 2015-era library README, which tracks with this sample's lean toward newer AI/dev-tooling projects that don't run traditional CI-coverage pipelines as visibly.

So "keep badges few" is not what this corpus does. What it does is keep them *typed*: a four-to-six badge row of license, version, stars, chat, and build, all wired to something real. The failure mode visible in the tail is a dozen-plus row where the marginal badge carries no information (ECC's 17), not the presence of a badge row as such.

Animated GIFs are uncommon (14%) despite being the single most-recommended "make people care" technique in generic README advice — actual demo proof in this corpus is far more likely to be a static screenshot, a linked hosted demo page (MoneyPrinterTurbo links out to a gallery of generated videos rather than embedding them), or a literal terminal transcript pasted as a code block (gstack, Graphify) than an inline animation.

## Links

Corpus-wide, across every Markdown-syntax link in all 100 READMEs: **96.8% are standard inline links (`[text](url)`), 3.0% are bare, unwrapped URLs, and 0.2% use reference-style syntax (`[text][ref]` with a separate definition list).** Reference-style links, despite being a "proper Markdown" technique taught in a lot of style guides, are functionally extinct in this corpus — 14 total links out of 5,851. Inline is the convention, full stop.

Bare URLs are the minority slip rather than the norm: 176 across the whole corpus, in half the repos, averaging under two per README. They still read badly (a long unbroken string, no descriptive text for a screen reader) and they still tend to appear in the same places — a table cell, a quick aside, a support address pasted mid-sentence — so wrapping them is worth doing. But the earlier version of this document called a 29% bare-URL rate "the one clear formatting anti-pattern the data shows," and that number was a parser artifact. See the correction note in Methodology. HTML `<a href>` links are excluded from these percentages entirely; they are a third style, common inside centered header blocks, and folding them into a Markdown-syntax ratio would measure something else again.

Where link text was measured (READMEs with at least a handful of inline links), the average link text length was **2.2 words** — link text names the destination ("see the docs," "our Discord," "the comparison doc") rather than using generic text like "here" or "this link," and rarely spans a full clause.

## Qualitative patterns from the top 20

These are the specific, named techniques that showed up repeatedly across the twenty highest-star repos read in full. Each is grounded in an actual repo; see `readme-analysis/repos/<slug>/qualitative_note.md` for the full note and more quotes.

**Show the mechanism before the pitch.** [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) and [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) both open with an ASCII-art pipeline diagram (`DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP`) that communicates the tool's mental model before a word of prose does. [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) and [garrytan/gstack](https://github.com/garrytan/gstack) do the prose version of the same thing: a real, reproducible terminal transcript instead of a staged screenshot or a claim.

**Argue against your own headline number.** The single strongest credibility pattern in the whole batch: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) explicitly walks back an earlier "80–94% less code" marketing claim as a "conversational-baseline artifact" and links the fuller writeup. [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) has an "honest number warning" callout stating its own headline stat "can go net-negative" on some workloads. [ruvnet/RuView](https://github.com/ruvnet/RuView) labels every claim by evidence tier ("Real & validated" vs. "Real but weak (honestly labeled)" vs. "Architecture only, no weights") and explicitly retracts an old figure in the text. A README that argues against its own hype reads as more trustworthy than one that only argues for it — this shows up across three unrelated repos as a deliberate device, not a fluke.

**Progressive disclosure via `<details>` accordions.** Nearly every long README in the top 20 tucks deep reference material — per-integration install steps, architecture diagrams, full command references — into collapsible `<details>` blocks, keeping the primary scroll short while keeping depth discoverable. [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) does this cleanly (only Claude Code expanded by default, everything else collapsed); [farion1231/cc-switch](https://github.com/farion1231/cc-switch) and [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) key their collapsed FAQ entries to literal error strings so they're still `Ctrl+F`-able.

**Tables over bullet sprawl for anything enumerable.** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)'s six-row capability table and [github/spec-kit](https://github.com/github/spec-kit)'s "when to use which" decision table both do work that a bullet list would make you scroll past. [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) gets scannability a different way — a terse, consistent one-line descriptor after every catalog entry, turning a flat link list into something you can skim by eye.

**A sustained voice, when the product supports it.** [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) writes parts of its own README in the broken "caveman speak" its tool produces ("why use many token when few do trick"); [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) sustains a single grumpy-senior-dev metaphor through headers, taglines, and FAQ answers. This only works because the bit *is* the product's actual behavior — it would read as try-hard on a README for, say, a database driver.

**Security and trust disclosures placed ahead of the pitch, not buried in a footer.** [microsoft/markitdown](https://github.com/microsoft/markitdown) puts an `[!IMPORTANT]` security callout before the reader learns what the tool converts. [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) includes a full antivirus-false-positive troubleshooting section with a copy-pasteable PowerShell attestation script. [earendil-works/pi](https://github.com/earendil-works/pi) lists concrete supply-chain hardening practices (`save-exact=true`, lockfile pre-commit blocking) rather than a vague security promise.

**Anti-patterns worth naming.** The most common failure mode in this batch is a wall of sponsor/promotional content sitting above the actual product description — [affaan-m/ECC](https://github.com/affaan-m/ECC) doesn't reach a real "what is this" until line 107, after a hero image, a 12-language link bar, four rows of badges, and a sponsor table; [farion1231/cc-switch](https://github.com/farion1231/cc-switch) puts a ~20-row collapsible sponsor table above its own product pitch; [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) does the same before its feature list. A second, related anti-pattern is an install section so branched it becomes a decision tree instead of a quickstart — ECC's dozens of nested `<details>` covering guided/manual/per-harness/low-context paths, each with warnings not to combine them, is the clearest example. Both point to the same underlying rule: **whatever appears before the first real description of what the thing does is a tax on every future reader.**

## Distilled checklist

This is the operational summary the `readme-writing` skill applies. Each line is backed by a number or a named repo above.

1. State what the thing does and why, in the first two sentences — before any badge row, sponsor content, or hero image. (ECC and cc-switch are the cautionary examples; markitdown and pi are the terse counter-examples.)
2. Order: pitch/features → fastest path to running it (installation) → depth (architecture, API, config) for people still reading → contributing/credits → license last. This is the measured convention across 100 repos, not a stylistic preference.
3. Centering the header block (logo/title/tagline/badges) is now majority convention (76%) — do it unless there's a specific reason toward a plainer, document-style open.
4. Keep badges typed rather than few: license, version/package, stars, chat, and build status are what the corpus actually carries, at a median of 5. Every badge should be wired to something real; the anti-pattern is the dozen-plus row where the marginal badge says nothing (ECC's 17).
5. Use inline Markdown links (`[text](url)`), not reference-style (functionally unused — 0.2% of links in this corpus). Wrap bare URLs: they are only 3.0% of links, so writing one puts you in a small minority, and it costs a screen reader the destination. Link text should name the destination in a couple of words, not say "here."
6. Vary sentence length on purpose — short declarative sentences mixed with longer explanatory ones (measured mix in this corpus: ~38% short / 37% medium / 26% long). Keep paragraphs to 2–3 sentences (corpus median: 28 words).
7. Show the mechanism, don't just claim it: a real terminal transcript, a before/after diff, or an ASCII pipeline diagram beats a paragraph of adjectives.
8. If a claim has a number attached, say what the number doesn't cover. The most credible READMEs in this sample all argue against their own headline stat somewhere.
9. For anything with more than ~4 install variants or platform branches, use collapsible `<details>` blocks instead of flattening it all into the main scroll — but keep the primary path (the one most readers want) expanded by default.
10. Put security/trust disclosures near the top if the tool touches the filesystem, network, or untrusted input — not in a buried footer section.
11. License section can and should be short — state the license and link the file. Median across the corpus is 13 words; nobody is reading legal text in a README.

## Limitations

This sample is heavily weighted toward AI/agent tooling and developer CLIs because that's what was growing fastest on GitHub in the trailing quarter as of August 2026 — it is not a representative sample of GitHub as a whole, and conventions here (e.g., a "Claude Code integration" section, or install instructions branched by AI harness) reflect that moment specifically. The heading-classification heuristic is keyword-based, not a certified parser, so category counts carry a margin of error of a few percent. Sentence splitting is a lightweight regex, not a proper NLP sentence boundary detector, so length statistics should be read as directionally accurate rather than exact. And "stars gained in the trailing 3 months" was the best available public proxy for "stars gained in the past year" — see Methodology above for why the exact query the brief asked for wasn't reachable from this environment.

## Reproducing this

Everything here was generated by the scripts in `scripts/readme-research/` (candidate fetch → metadata/README enrichment → per-repo analysis → corpus aggregation) plus one hand-written qualitative pass over the top 20. Raw and intermediate data:

- `readme-analysis/01_ranked_repos.json` — the full ranked population with metadata
- `readme-analysis/02_all_stats.json` — every repo's computed stats in one file
- `readme-analysis/03_aggregate_summary.json` — the corpus-wide numbers this document is built from
- `readme-analysis/repos/<owner>__<repo>/` — per-repo README, stats, and (top 20) qualitative note
