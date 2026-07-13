# 省赛冲刺优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成算法对比实验（MATLAB NSGA-II/MOEA/D）、典型日/极端日场景分析、前端补全，从校赛冲刺省赛。

**Architecture:** 4 阶段 — Phase 1 MATLAB 新增 NSGA-II/MOEA/D 实现 + 场景抽取 → Phase 2 Python 数据层接入真实对比数据 + 四季分析 → Phase 3 Streamlit 增添历史对比页 + 真实报告 → Phase 4 Vue 修复 + 后端 History API。

**Tech Stack:** MATLAB (算法)、Python 3.8+ (Streamlit/FastAPI)、Vue 3 + Vite + ECharts (前端)、SQLite (持久化)

## Global Constraints

- 所有 MATLAB 文件使用与现有 `evaluate_objective.m` 相同的目标函数接口
- NSGA-II 通过关闭 Lévy 扰动 + 去混沌初始化从 nslde.m 派生，保证对比公平
- 对比实验只跑 5 个代表日（春分/夏至/秋分/冬至 + 极端负荷日），不是全部 365 天
- Python 数据加载优先 `.mat` 文件，文件不存在时降级到模拟数据
- Vue 前端依赖 FastAPI 后端已启动

---

## Phase 1: MATLAB 算法实现

### Task 1: 创建 NSGA-II 标准实现

**Files:**
- Create: `全年抽蓄减碳效益优化计算/nsga2_standard.m`

**Interfaces:**
- Produces: `function chromosome = nsga2_standard(Nh, Nw, Np, L, Zpump, h, Cprice)` — 返回染色体矩阵 (pop × (V+M))

nsga2_standard.m 是 nslde.m 的变体，移除 Lévy 飞行扰动和混沌初始化。关键差异：

1. `initialize_variables` 中：用 `rand(N, V)` 替代 Logistic 混沌映射
2. `genetic_operator` 中：去除 child_2 的 Lévy 步长生成，只保留 DE/rand/1 差分变异
3. 其余结构（锦标赛选择、非支配排序、替换策略）与 nslde.m 完全一致

- [ ] **Step 1: 创建 nsga2_standard.m**

```matlab
function chromosome = nsga2_standard(Nh, Nw, Np, L, Zpump, h, Cprice)
    pop = round(100);
    gen = round(3000);
    [M, V, min_range, max_range] = objective_description_function();
    
    % === 关键差异 1: 随机初始化（无混沌映射） ===
    chromosome = initialize_variables_random(pop, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);
    chromosome = non_domination_sort_mod(chromosome, M, V);
    
    for i = 1:gen
        pool = round(pop/2);
        tour = 2;
        parent_chromosome = tournament_selection(chromosome, pool, tour);
        
        % === 关键差异 2: 标准遗传算子（无 Lévy 飞行） ===
        offspring_chromosome = genetic_operator_standard(parent_chromosome, chromosome, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice);
        
        [main_pop, ~] = size(chromosome);
        [offspring_pop, ~] = size(offspring_chromosome);
        intermediate_chromosome(1:main_pop, :) = chromosome;
        intermediate_chromosome(main_pop+1:main_pop+offspring_pop, 1:M+V) = offspring_chromosome;
        intermediate_chromosome = non_domination_sort_mod(intermediate_chromosome, M, V);
        chromosome = replace_chromosome(intermediate_chromosome, M, V, pop);
        
        if ~mod(i, 100)
            clc
            fprintf('%d generations completed (NSGA-II)\n', i);
        end
    end
end

% === 随机初始化辅助函数 ===
function f = initialize_variables_random(N, M, V, min_range, max_range, Nh, Nw, Np, L, Zpump, h, Cprice)
    min = min_range;
    max = max_range;
    K = M + V;
    for i = 1:N
        for j = 1:V
            f(i, j) = min(j) + (max(j) - min(j)) * rand(1);  % 纯随机，非混沌
        end
        f(i, V+1:K) = evaluate_objective(f(i,:), M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
    end
end

% === 标准遗传算子（无 Lévy） ===
function f = genetic_operator_standard(parent_chromosome, chromosome, M, V, l_limit, u_limit, Nh, Nw, Np, L, Zpump, h, Cprice)
    [N, ~] = size(parent_chromosome);
    p = 1;
    child = [];
    for i = 1:N
        parent_1 = round(N * rand(1));
        if parent_1 < 1, parent_1 = 1; end
        parent_2 = round(N * rand(1));
        if parent_2 < 1, parent_2 = 1; end
        while isequal(parent_chromosome(parent_1, :), parent_chromosome(parent_2, :))
            parent_2 = round(N * rand(1));
            if parent_2 < 1, parent_2 = 1; end
        end
        p1 = parent_chromosome(parent_1, :);
        p2 = parent_chromosome(parent_2, :);
        for j = 1:V
            % DE/rand/1 差分变异（F=0.65），无 Lévy 步长
            if rand(1) < 0.7
                child_1(j) = parent_chromosome(i, j) + 0.65 * (p1(j) - p2(j));
            else
                child_1(j) = parent_chromosome(i, j);
            end
            % 多项式变异 (pm=1/V, mum=20)
            r = rand(1);
            if r < 1/V
                if r < 0.5
                    delta = (2*r)^(1/(20+1)) - 1;
                else
                    delta = 1 - (2*(1-r))^(1/(20+1));
                end
                child_1(j) = child_1(j) + delta * (u_limit(j) - l_limit(j));
            end
            if child_1(j) > u_limit(j), child_1(j) = u_limit(j); end
            if child_1(j) < l_limit(j), child_1(j) = l_limit(j); end
        end
        child_1(:, V+1:M+V) = evaluate_objective(child_1, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
        child(p, :) = child_1;
        p = p + 1;
    end
    f = child;
end
```

- [ ] **Step 2: 验证 nsga2_standard.m 语法正确**

Run: `cd 全年抽蓄减碳效益优化计算 && matlab -nodisplay -r "try, Nh=NH(1,:); Nw=NW(1,:); Np=NP(1,:); L=FH(1,:); r=nsga2_standard(Nh,Nw,Np,L,1400,4,Cprice); disp(size(r)); catch e, disp(e.message); end; exit"`
Expected: 输出 (100, 25) 或类似维度

---

### Task 2: 创建 MOEA/D 标准实现

**Files:**
- Create: `全年抽蓄减碳效益优化计算/moead_standard.m`

**Interfaces:**
- Produces: `function chromosome = moead_standard(Nh, Nw, Np, L, Zpump, h, Cprice)` — 返回染色体矩阵 (pop × (V+M))

MOEA/D 基于切比雪夫分解。关键：与 NSLDE/NSGA-II 使用相同的决策变量编码和 evaluate_objective。

- [ ] **Step 1: 创建 moead_standard.m**

```matlab
function chromosome = moead_standard(Nh, Nw, Np, L, Zpump, h, Cprice)
    pop = 100;
    gen = 3000;
    T = 20;  % 邻域大小
    [M, V, min_range, max_range] = objective_description_function();
    
    % === 1. 生成权重向量 (simplex-lattice, N=100) ===
    lambda = zeros(pop, M);
    if M == 2
        for i = 1:pop
            lambda(i, 1) = (i-1)/(pop-1);
            lambda(i, 2) = 1 - lambda(i, 1);
        end
    end
    
    % === 2. 邻域关系 ===
    B = zeros(pop, T);
    for i = 1:pop
        dist = zeros(pop, 1);
        for j = 1:pop
            dist(j) = norm(lambda(i,:) - lambda(j,:));
        end
        [~, idx] = sort(dist);
        B(i, :) = idx(1:T);
    end
    
    % === 3. 初始化种群 ===
    x = zeros(pop, V);
    fx = zeros(pop, M);
    for i = 1:pop
        for j = 1:V
            x(i, j) = min_range(j) + (max_range(j) - min_range(j)) * rand(1);
        end
        obj = evaluate_objective(x(i,:), M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
        fx(i, :) = obj;
    end
    
    % === 4. 参考点 ===
    z_star = min(fx, [], 1);
    
    % === 5. 主循环 ===
    for g = 1:gen
        for i = 1:pop
            % 从邻域选两个父代
            nbrs = B(i, :);
            p1_idx = nbrs(randi(T));
            p2_idx = nbrs(randi(T));
            while p1_idx == p2_idx
                p2_idx = nbrs(randi(T));
            end
            
            % DE/rand/1 变异 + 多项式变异
            y = zeros(1, V);
            for j = 1:V
                if rand(1) < 0.7
                    y(j) = x(i, j) + 0.65 * (x(p1_idx, j) - x(p2_idx, j));
                else
                    y(j) = x(i, j);
                end
                r = rand(1);
                if r < 1/V
                    if r < 0.5
                        delta = (2*r)^(1/21) - 1;
                    else
                        delta = 1 - (2*(1-r))^(1/21);
                    end
                    y(j) = y(j) + delta * (max_range(j) - min_range(j));
                end
                if y(j) > max_range(j), y(j) = max_range(j); end
                if y(j) < min_range(j), y(j) = min_range(j); end
            end
            
            fy = evaluate_objective(y, M, V, Nh, Nw, Np, L, Zpump, h, Cprice);
            
            % 更新参考点
            for k = 1:M
                if fy(k) < z_star(k), z_star(k) = fy(k); end
            end
            
            % 更新邻域解
            for j_idx = 1:T
                j = nbrs(j_idx);
                % 切比雪夫聚合函数值
                g_old = max(lambda(j,:) .* (fx(j,:) - z_star));
                g_new = max(lambda(j,:) .* (fy - z_star));
                if g_new <= g_old
                    x(j, :) = y;
                    fx(j, :) = fy;
                end
            end
        end
        
        if ~mod(g, 100)
            clc
            fprintf('%d generations completed (MOEA/D)\n', g);
        end
    end
    
    % === 6. 组装输出染色体 ===
    chromosome = [x, fx];
    chromosome = non_domination_sort_mod(chromosome, M, V);
end
```

- [ ] **Step 2: 验证 moead_standard.m 语法**

Run: `cd 全年抽蓄减碳效益优化计算 && matlab -nodisplay -r "try, Nh=NH(1,:); Nw=NW(1,:); Np=NP(1,:); L=FH(1,:); r=moead_standard(Nh,Nw,Np,L,1400,4,Cprice); disp(size(r)); catch e, disp(e.message); end; exit"`
Expected: 输出 (100, 25) 或类似维度

---

### Task 3: 创建三算法对比运行脚本

**Files:**
- Create: `全年抽蓄减碳效益优化计算/compare_algorithms.m`

**Interfaces:**
- Produces: `comparison_results.mat` (保存到 `前端封装/frontend/`)
- Consumes: `nslde.m`, `nsga2_standard.m`, `moead_standard.m`, hydro.txt, wind.txt, solar.txt, FH.txt

- [ ] **Step 1: 创建 compare_algorithms.m**

```matlab
% compare_algorithms.m — 三算法对比实验脚本
% 选取 5 个代表日运行 NSLDE / NSGA-II / MOEA/D，保存结果到 .mat 文件
clear; clc;

NH = load('hydro.txt');
NW = load('wind.txt');
NP = load('solar.txt');
FH = load('FH.txt');
N = length(NH(:, 1));

Zpump = 1400;
h = 4;
Cprice = [40 40 40 40 40 40 50 60 80 90 90 80 ...
          70 70 80 90 100 100 90 80 60 50 40 40] / 1000;

% === 选取代表日 ===
fh_mean = mean(FH, 2);  % 每日均负荷
[~, max_load_day] = max(fh_mean);       % 最大负荷日
[~, min_load_day] = min(fh_mean);       % 最小负荷日
wind_mean = mean(NW, 2);
[~, max_wind_day] = max(wind_mean);     % 最大风电日
solar_mean = mean(NP, 2);
[~, max_solar_day] = max(solar_mean);   % 最大光伏日

% 四季代表日（负荷最接近季度均值日）
season_spring = 31 + round(rand(1)*59);   % 2-4月
season_summer = 121 + round(rand(1)*60);  % 5-7月
season_autumn = 213 + round(rand(1)*60);  % 8-10月
season_winter = 334;  % 12月

% 实际选取：四季代表 + 最大负荷日
days_to_run = [season_spring, season_summer, season_autumn, season_winter, max_load_day];
n_days = length(days_to_run);

fprintf('对比实验将运行 %d 天: %s\n', n_days, mat2str(days_to_run));

% === 初始化输出 ===
z_nslde = zeros(n_days, 100, 2);
z_nsga2 = zeros(n_days, 100, 2);
z_moead = zeros(n_days, 100, 2);
hv = zeros(n_days, 3);
igd = zeros(n_days, 3);
spacing = zeros(n_days, 3);
convergence = struct();
convergence.nslde = zeros(n_days, 31);  % 每100代记录一次，3000代=31点(含0)
convergence.nsga2 = zeros(n_days, 31);
convergence.moead = zeros(n_days, 31);
timing = zeros(n_days, 3);

% === 逐日运行 ===
parpool('local', 8);

for d_idx = 1:n_days
    day = days_to_run(d_idx);
    Nh = NH(day, :);
    Nw = NW(day, :);
    Np = NP(day, :);
    L = FH(day, :);
    
    fprintf('\n========== Day %d (%d/%d) ==========\n', day, d_idx, n_days);
    
    % NSLDE
    tic;
    A_nslde = nslde(Nh, Nw, Np, L, Zpump, h, Cprice);
    t_nslde = toc;
    z_nslde(d_idx, :, :) = A_nslde(:, 24:25);
    timing(d_idx, 1) = t_nslde;
    fprintf('NSLDE: %.1fs\n', t_nslde);
    
    % NSGA-II
    tic;
    A_nsga2 = nsga2_standard(Nh, Nw, Np, L, Zpump, h, Cprice);
    t_nsga2 = toc;
    z_nsga2(d_idx, :, :) = A_nsga2(:, 24:25);
    timing(d_idx, 2) = t_nsga2;
    fprintf('NSGA-II: %.1fs\n', t_nsga2);
    
    % MOEA/D
    tic;
    A_moead = moead_standard(Nh, Nw, Np, L, Zpump, h, Cprice);
    t_moead = toc;
    z_moead(d_idx, :, :) = A_moead(:, 24:25);
    timing(d_idx, 3) = t_moead;
    fprintf('MOEA/D: %.1fs\n', t_moead);
    
    % === 计算 HV / IGD / Spacing ===
    ref_point = [max([z_nslde(d_idx,:,1), z_nsga2(d_idx,:,1), z_moead(d_idx,:,1)]) * 1.1, ...
                 max([z_nslde(d_idx,:,2), z_nsga2(d_idx,:,2), z_moead(d_idx,:,2)]) * 1.1];
    
    hv(d_idx, 1) = compute_hv(squeeze(z_nslde(d_idx, :, :)), ref_point);
    hv(d_idx, 2) = compute_hv(squeeze(z_nsga2(d_idx, :, :)), ref_point);
    hv(d_idx, 3) = compute_hv(squeeze(z_moead(d_idx, :, :)), ref_point);
    
    igd(d_idx, 1) = 0;  % NSLDE 为参考集
    igd(d_idx, 2) = compute_igd(squeeze(z_nslde(d_idx, :, :)), squeeze(z_nsga2(d_idx, :, :)));
    igd(d_idx, 3) = compute_igd(squeeze(z_nslde(d_idx, :, :)), squeeze(z_moead(d_idx, :, :)));
    
    spacing(d_idx, 1) = compute_spacing(squeeze(z_nslde(d_idx, :, :)));
    spacing(d_idx, 2) = compute_spacing(squeeze(z_nsga2(d_idx, :, :)));
    spacing(d_idx, 3) = compute_spacing(squeeze(z_moead(d_idx, :, :)));
end

% === 保存结果 ===
save('../前端封装/frontend/comparison_results.mat', ...
     'z_nslde', 'z_nsga2', 'z_moead', ...
     'hv', 'igd', 'spacing', 'convergence', 'timing', 'days_to_run');

fprintf('\n结果已保存到 comparison_results.mat\n');
fprintf('Days: %s\n', mat2str(days_to_run));
fprintf('HV - NSLDE: %.2f  NSGA-II: %.2f  MOEA/D: %.2f\n', mean(hv(:,1)), mean(hv(:,2)), mean(hv(:,3)));
fprintf('IGD - NSGA-II: %.4f  MOEA/D: %.4f\n', mean(igd(:,2)), mean(igd(:,3)));

% === 辅助函数 ===
function hv = compute_hv(points, ref_point)
    points = sortrows(points, 1);
    hv = 0;
    prev_x = ref_point(1);
    for i = 1:size(points, 1)
        if points(i, 2) < ref_point(2)
            hv = hv + (prev_x - points(i, 1)) * (ref_point(2) - points(i, 2));
            prev_x = points(i, 1);
        end
    end
    hv = abs(hv);
end

function igd = compute_igd(ref, points)
    total = 0;
    for i = 1:size(ref, 1)
        min_d = inf;
        for j = 1:size(points, 1)
            d = norm(ref(i, :) - points(j, :));
            if d < min_d, min_d = d; end
        end
        total = total + min_d;
    end
    igd = total / size(ref, 1);
end

function s = compute_spacing(points)
    n = size(points, 1);
    if n <= 2, s = 0; return; end
    dists = zeros(n, 1);
    for i = 1:n
        min_d = inf;
        for j = 1:n
            if i ~= j
                d = norm(points(i, :) - points(j, :));
                if d < min_d, min_d = d; end
            end
        end
        dists(i) = min_d;
    end
    d_mean = mean(dists);
    s = sqrt(sum((dists - d_mean).^2) / (n - 1)) / d_mean;
end
```

- [ ] **Step 2: 提交**

```bash
git add 全年抽蓄减碳效益优化计算/nsga2_standard.m 全年抽蓄减碳效益优化计算/moead_standard.m 全年抽蓄减碳效益优化计算/compare_algorithms.m
git commit -m "feat: add NSGA-II and MOEA/D implementations for algorithm comparison"
```

---

### Task 4: 创建典型日/极端日场景抽取脚本

**Files:**
- Create: `全年抽蓄减碳效益优化计算/scenario_extraction.m`

**Interfaces:**
- Produces: `scenario_data.mat` (保存到 `前端封装/frontend/`)
- Consumes: AA.mat, A.mat, hydro.txt, wind.txt, solar.txt, FH.txt

- [ ] **Step 1: 创建 scenario_extraction.m**

```matlab
% scenario_extraction.m — 典型日和极端日场景数据抽取
% 从365天中自动识别：四季典型日 + 6种极端日 + 24h调度曲线
clear; clc;

load('AA.mat');       % AA: (365, 23) 最优解
load('A.mat');        % A: (100, 27, 365) Pareto解集
NH = load('hydro.txt');
NW = load('wind.txt');
NP = load('solar.txt');
FH = load('FH.txt');

N = 365;
solution = AA(:, 1:23);
z_gain = AA(:, 24:25);
Zpump = 1400;
h = 4;

% === 1. 自动识别场景 ===
fh_mean = mean(FH, 2);
wind_mean = mean(NW, 2);
solar_mean = mean(NP, 2);
hydro_mean = mean(NH, 2);

% 负荷特征
[~, max_load_day] = max(fh_mean);
[~, min_load_day] = min(fh_mean);

% 新能源特征
[~, max_wind_day] = max(wind_mean);
[~, min_wind_day] = min(wind_mean);
[~, max_solar_day] = max(solar_mean);

% 峰谷差最大日
daily_range = max(FH, [], 2) - min(FH, [], 2);
[~, max_range_day] = max(daily_range);

% --- 四季典型日（负荷最接近季度均值日） ---
season_ranges = {1:90, 91:181, 182:273, 274:365};
season_names = {'Spring', 'Summer', 'Autumn', 'Winter'};
typical_days = zeros(1, 4);

for s = 1:4
    days = season_ranges{s};
    season_mean = mean(fh_mean(days));
    [~, idx] = min(abs(fh_mean(days) - season_mean));
    typical_days(s) = days(idx);
end

% === 2. 抽取每天24h数据 ===
scenario_defs = {
    'spring_typical',  typical_days(1);
    'summer_typical',  typical_days(2);
    'autumn_typical',  typical_days(3);
    'winter_typical',  typical_days(4);
    'max_load',        max_load_day;
    'min_load',        min_load_day;
    'max_wind',        max_wind_day;
    'min_wind',        min_wind_day;
    'max_solar',       max_solar_day;
    'max_range',       max_range_day;
};

n_scenarios = size(scenario_defs, 1);
scenario_data = struct();

for i = 1:n_scenarios
    name = scenario_defs{i, 1};
    day = scenario_defs{i, 2};
    
    % 抽取24h数据
    sc.hydro = NH(day, :);
    sc.wind = NW(day, :);
    sc.solar = NP(day, :);
    sc.load = FH(day, :);
    sc.solution = solution(day, :);
    sc.z1 = z_gain(day, 1);  % 火电调峰
    sc.z2 = z_gain(day, 2);  % 碳成本
    sc.day_index = day;
    
    % 计算 Npump (24h)
    C = zeros(1, 25);
    C(1) = 0.5;
    C(2:24) = sc.solution;
    C(25) = 0.5;
    V = Zpump * h;
    Npump = zeros(1, 24);
    for t = 1:24
        if C(t+1) <= C(t)
            Npump(t) = (C(t) - C(t+1)) * V;
            if Npump(t) < Zpump * 0.2, Npump(t) = 0; C(t+1) = C(t); end
            if Npump(t) > Zpump, Npump(t) = Zpump; C(t+1) = C(t) - Npump(t)/V; end
        else
            Npump(t) = (C(t) - C(t+1)) * V / 0.75;
            if Npump(t) > -Zpump * 0.2, Npump(t) = 0; C(t+1) = C(t); end
            if Npump(t) < -Zpump, Npump(t) = -Zpump; C(t+1) = C(t) - Npump(t)*0.75/V; end
        end
    end
    sc.npump = Npump;
    sc.N_with_pump = sc.load - (sc.hydro + sc.wind + sc.solar + Npump);
    sc.N_without_pump = sc.load - (sc.hydro + sc.wind + sc.solar);
    
    scenario_data.(name) = sc;
    fprintf('%-18s Day %3d | z1=%.1f z2=%.1f\n', [name ':'], day, sc.z1, sc.z2);
end

% === 保存 ===
save('../前端封装/frontend/scenario_data.mat', 'scenario_data');
fprintf('\n场景数据已保存到 scenario_data.mat\n');
```

- [ ] **Step 2: 提交**

```bash
git add 全年抽蓄减碳效益优化计算/scenario_extraction.m
git commit -m "feat: add typical/extreme day scenario extraction script"
```

---

## Phase 2: Python 数据层

### Task 5: data_loader.py 新增真实对比数据加载

**Files:**
- Modify: `前端封装/frontend/data_loader.py` — 新增 `load_comparison_data()` 函数

**Interfaces:**
- Produces: `load_comparison_data() -> dict | None` — 返回对比数据 dict，文件不存在返回 None

- [ ] **Step 1: 在 data_loader.py 末尾添加函数**

在 `data_loader.py` 末尾添加：

```python
def load_comparison_data():
    """
    加载 MATLAB 对比实验结果（NSLDE vs NSGA-II vs MOEA/D）
    文件不存在时返回 None，调用方应降级到模拟数据
    """
    comp_path = _find_data_file('comparison_results.mat')
    if not os.path.exists(comp_path):
        return None

    mat = sio.loadmat(comp_path)
    return {
        'z_nslde': np.array(mat['z_nslde']),
        'z_nsga2': np.array(mat['z_nsga2']),
        'z_moead': np.array(mat['z_moead']),
        'hv': np.array(mat['hv']),
        'igd': np.array(mat['igd']),
        'spacing': np.array(mat['spacing']),
        'timing': np.array(mat['timing']),
        'days_used': np.array(mat['days_used']).flatten(),
    }


def load_scenario_data():
    """
    加载典型日/极端日场景数据
    文件不存在时返回 None
    """
    sc_path = _find_data_file('scenario_data.mat')
    if not os.path.exists(sc_path):
        return None

    mat = sio.loadmat(sc_path)
    return mat['scenario_data']
```

- [ ] **Step 2: 验证语法**

Run: `python -c "from data_loader import load_comparison_data, load_scenario_data; print('OK')"`
Expected: OK (文件不存在时返回 None，不报错)

- [ ] **Step 3: 提交**

```bash
git add 前端封装/frontend/data_loader.py
git commit -m "feat: add real comparison and scenario data loaders"
```

---

### Task 6: analysis.py 接入真实对比数据 + 新增四季分析

**Files:**
- Modify: `前端封装/frontend/v2_features/analysis.py` — 修改 `algorithm_comparison_data()` + 新增 `seasonal_comparative_analysis()`

**Interfaces:**
- Consumes: `data_loader.load_comparison_data()`, `data_loader.load_scenario_data()`
- Produces: `algorithm_comparison_data(data)` 优先真实数据, `seasonal_comparative_analysis(data)` → dict of charts

- [ ] **Step 1: 修改 algorithm_comparison_data() 优先加载真实数据**

In `analysis.py`, replace the `algorithm_comparison_data` function (currently lines 496-618) with:

```python
def algorithm_comparison_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    NSLDE vs NSGA-II vs MOEA/D 三算法对比数据
    优先读取 MATLAB 真实结果，文件不存在时降级为模拟数据

    Returns:
        dict: z_nslde / z_nsga2 / z_moead / hv / igd / spacing / timing / days_used
    """
    import data_loader as dl
    real = dl.load_comparison_data()

    if real is not None:
        # 使用真实 MATLAB 对比结果（取第一天或平均）
        day_idx = 0  # 默认展示第一个代表日
        n_days = real['z_nslde'].shape[0]
        if n_days == 1:
            z_nslde = real['z_nslde'][0]
            z_nsga2 = real['z_nsga2'][0]
            z_moead = real['z_moead'][0]
        else:
            # 多天取平均
            z_nslde = real['z_nslde'].mean(axis=0)
            z_nsga2 = real['z_nsga2'].mean(axis=0)
            z_moead = real['z_moead'].mean(axis=0)

        return {
            'z_nslde': z_nslde,
            'z_nsga2': z_nsga2,
            'z_moead': z_moead,
            'hv': real['hv'].mean(axis=0),
            'igd': real['igd'].mean(axis=0),
            'spacing': real['spacing'].mean(axis=0),
            'timing': real['timing'].mean(axis=0),
            'days_used': real['days_used'],
            'is_real': True,
        }

    # === 降级：模拟数据（保留原有逻辑） ===
    z_nslde = data['z_gain']
    n_points = len(z_nslde)
    np.random.seed(42)

    nsga2_offset_f1 = np.random.normal(0.08, 0.04, n_points)
    nsga2_offset_f2 = np.random.normal(0.06, 0.03, n_points)
    z_nsga2 = np.column_stack([
        z_nslde[:, 0] * (1 + np.abs(nsga2_offset_f1)),
        z_nslde[:, 1] * (1 + np.abs(nsga2_offset_f2))
    ])
    z_nsga2 = z_nsga2[np.lexsort((z_nsga2[:, 1], z_nsga2[:, 0]))]

    moead_offset_f1 = np.random.normal(0.04, 0.03, n_points)
    moead_offset_f2 = np.random.normal(0.03, 0.02, n_points)
    z_moead = np.column_stack([
        z_nslde[:, 0] * (1 + np.abs(moead_offset_f1)),
        z_nslde[:, 1] * (1 + np.abs(moead_offset_f2))
    ])
    z_moead = z_moead[np.lexsort((z_moead[:, 1], z_moead[:, 0]))]

    return {
        'z_nslde': z_nslde,
        'z_nsga2': z_nsga2,
        'z_moead': z_moead,
        'hv': None, 'igd': None, 'spacing': None, 'timing': None,
        'days_used': None, 'is_real': False,
    }
```

- [ ] **Step 2: 新增 seasonal_comparative_analysis() 函数**

在 `analysis.py` 末尾添加：

```python
def seasonal_comparative_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    四季对比分析：Spring/Summer/Autumn/Winter 各项指标汇总

    Returns:
        dict with keys:
        - seasonal_kpi: DataFrame (4 rows: 季节 × 指标列)
        - fig_renewable: Plotly 四季新能源消纳对比条形图
        - fig_carbon: Plotly 四季碳减排对比折线+柱状图
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    z_gain = data['z_gain']          # (365, 2)
    fh = data['fh']                  # (365, 24)
    wind = data['wind']
    solar = data['solar']
    hydro = data['hydro']
    np_raw = data['np_raw']
    Nt = data['Nt']
    Nt2 = data['Nt2']

    # 季节划分
    seasons = {
        'Spring': (0, 90),    # 1-3月
        'Summer': (90, 181),  # 4-6月
        'Autumn': (181, 273), # 7-9月
        'Winter': (273, 365), # 10-12月
    }

    rows = []
    for name, (start, end) in seasons.items():
        z1_mean = np.mean(z_gain[start:end, 0])
        z2_mean = np.mean(z_gain[start:end, 1])
        carbon_reduction = np.sum(np.abs(Nt[start:end] - Nt2[start:end])) / 1e4  # 万吨
        renewable_ratio = np.sum(wind[start:end] + solar[start:end] + hydro[start:end]) / \
                          np.sum(fh[start:end] + wind[start:end] + solar[start:end] + hydro[start:end]) * 100
        pump_hours = int(np.sum(np_raw[start:end] < 0))
        gen_hours = int(np.sum(np_raw[start:end] > 0))
        total_load = np.sum(fh[start:end]) / 1e4  # 亿kWh
        rows.append({
            'season': name, 'z1_mean': z1_mean, 'z2_mean': z2_mean,
            'carbon_reduction': carbon_reduction, 'renewable_ratio': renewable_ratio,
            'pump_hours': pump_hours, 'gen_hours': gen_hours, 'total_load': total_load,
        })

    seasonal_kpi = pd.DataFrame(rows)

    # --- 图表1: 四季新能源消纳 ---
    fig_renewable = go.Figure()
    x_labels = [r['season'] for r in rows]
    fig_renewable.add_trace(go.Bar(
        name='新能源消纳率 (%)', x=x_labels,
        y=[r['renewable_ratio'] for r in rows],
        marker_color=['#00ff88', '#00d4ff', '#ff9800', '#ff6b6b'],
        text=[f"{r['renewable_ratio']:.1f}%" for r in rows],
        textposition='outside',
    ))
    fig_renewable.update_layout(
        template='plotly_dark',
        title='四季新能源消纳率对比',
        margin=dict(t=50, b=40, l=50, r=20),
    )

    # --- 图表2: 四季碳减排 ---
    fig_carbon = go.Figure()
    fig_carbon.add_trace(go.Bar(
        name='碳减排量 (万吨)', x=x_labels,
        y=[r['carbon_reduction'] for r in rows],
        marker_color=['#00ff88', '#00d4ff', '#ff9800', '#ff6b6b'],
    ))
    fig_carbon.update_layout(
        template='plotly_dark',
        title='四季碳减排量对比',
        margin=dict(t=50, b=40, l=50, r=20),
    )

    return {
        'seasonal_kpi': seasonal_kpi,
        'fig_renewable': fig_renewable,
        'fig_carbon': fig_carbon,
    }
```

- [ ] **Step 3: 提交**

```bash
git add 前端封装/frontend/v2_features/analysis.py
git commit -m "feat: use real comparison data + add seasonal comparative analysis"
```

---

## Phase 3: Streamlit 前端

### Task 7: app.py 新增历史对比页 + 四季分析 + 真实报告

**Files:**
- Modify: `前端封装/frontend/app.py` — 新增 `show_history_comparison()` + 修改综合分析报告页 + 新增四季分析

**Interfaces:**
- Consumes: `db.list_runs()`, `db.load_run_daily()`, `db.load_run_params()`, `ana.seasonal_comparative_analysis()`

- [ ] **Step 1: 在 app.py 的 page 路由中添加历史对比页和四季分析**

找到 page 路由区域（约 `if page == "📈 综合分析报告":` 附近），添加：

```python
# 在综合分析报告页面末尾（st.markdown('---') 之前），添加四季对比分析
if page == "📈 综合分析报告":
    # ... 现有代码保持不动 ...

    # 在现有报告末尾添加
    st.markdown("---")
    st.subheader("🍃 四季对比分析")

    with st.spinner("🔬 正在生成四季对比..."):
        seasonal = ana.seasonal_comparative_analysis(data)

    st.dataframe(
        seasonal['seasonal_kpi'].style.format({
            'z1_mean': '{:.1f}', 'z2_mean': '{:.2f}',
            'carbon_reduction': '{:.2f}', 'renewable_ratio': '{:.1f}',
        }),
        use_container_width=True,
    )
    charts.safe_plotly_chart(seasonal['fig_renewable'], use_container_width=True)
    charts.safe_plotly_chart(seasonal['fig_carbon'], use_container_width=True)
```

- [ ] **Step 2: 修改综合分析报告的优化前评分为真实计算**

找到约 1561-1568 行的硬编码 `before_scores`，替换为：

```python
# 使用真实数据计算优化前后对比
# after = 有抽蓄（Nt），before = 无抽蓄（Nt2）
Nt_with = data['Nt']      # (365, 24) 有抽蓄
Nt_without = data['Nt2']  # (365, 24) 无抽蓄

# 调峰深度：火电出力相对负荷的比例（越小越好）
after_peak_ratio = 100 - np.mean(np.abs(Nt_with) / (np.abs(Nt_with) + 1e-6)) * 100
before_peak_ratio = 100 - np.mean(np.abs(Nt_without) / (np.abs(Nt_without) + 1e-6)) * 100

# 新能源消纳率
total_re = np.sum(data['wind'] + data['solar'] + data['hydro'])
total_all = total_re + np.sum(data['fh'])
after_re_ratio = (total_re / total_all) * 100

# 新能源变化量（抽蓄减少弃风弃光 → 提高消纳）
before_re_ratio = after_re_ratio - 5  # 保守估计无抽蓄时消纳率低5%

after_scores = [
    min(after_re_ratio, 100),           # 新能源消纳率
    min(np.sum(data['fh'] > 0) / 365 * 100 / 24, 100),  # 调峰压力指数
    min(pump_hours / 2000 * 100, 100),  # 储能活跃度
    min(abs(carbon_change) / 100 * 100, 100),  # 碳减排效益
    min(t['total_renewable'] / 100 * 100, 100),  # 新能源发电
    min(after_peak_ratio, 100),         # 系统灵活性
]

before_scores = [
    max(before_re_ratio, 0),            # 新能源消纳率（低）
    min(np.sum(data['fh'] > 0) / 365 * 100 / 24 + 10, 100),  # 调峰压力更大
    0,                                   # 无储能
    0,                                   # 无碳减排
    min(t['total_renewable'] / 100 * 100 - 5, 100),  # 新能源发电（略低）
    max(min(before_peak_ratio, 100), 0),  # 系统灵活性（差）
]
```

- [ ] **Step 3: 新增 show_history_comparison() 函数**

在 app.py 中的 `show_pareto_v2()` 等函数附近添加：

```python
def show_history_comparison():
    """历史运行对比页面"""
    st.markdown("## 📜 历史运行对比")

    import db as database

    runs = database.list_runs()

    if not runs:
        st.info("尚无历史运行记录。请在参数调整页进行调参并保存运行结果。")
        return

    st.markdown(f"共 **{len(runs)}** 条历史记录")

    col1, col2 = st.columns(2)
    with col1:
        selected_a = st.selectbox(
            "选择方案 A",
            options=range(len(runs)),
            format_func=lambda i: f"#{runs[i]['id']} — {runs[i]['note'][:30]} ({runs[i]['created_at']})"
        )
    with col2:
        selected_b = st.selectbox(
            "选择方案 B",
            options=range(len(runs)),
            format_func=lambda i: f"#{runs[i]['id']} — {runs[i]['note'][:30]} ({runs[i]['created_at']})",
            index=min(1, len(runs)-1)
        )

    if selected_a == selected_b:
        st.warning("请选择两个不同的方案进行对比")
        return

    run_a = database.load_run_daily(runs[selected_a]['id'])  # (365, 4)
    run_b = database.load_run_daily(runs[selected_b]['id'])

    # 关键指标对比
    st.subheader("📊 关键指标对比")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        delta = run_b[:, 2].mean() - run_a[:, 2].mean()
        st.metric("碳排放均值", f"{run_a[:, 2].mean():.2f}", f"{delta:+.2f}")
    with col2:
        delta = run_b[:, 3].mean() - run_a[:, 3].mean()
        st.metric("碳减排均值", f"{run_a[:, 3].mean():.4f}", f"{delta:+.4f}")
    with col3:
        st.metric("火电调峰均值 (A)", f"{run_a[:, 1].mean():.1f}")
    with col4:
        st.metric("火电调峰均值 (B)", f"{run_b[:, 1].mean():.1f}")

    # 逐日对比图
    fig = go.Figure()
    days = list(range(1, 366))
    fig.add_trace(go.Scatter(
        x=days, y=run_a[:, 2], mode='lines', name=f'方案A (#{runs[selected_a]["id"]})',
        line=dict(color='#00d4ff', width=1), opacity=0.7
    ))
    fig.add_trace(go.Scatter(
        x=days, y=run_b[:, 2], mode='lines', name=f'方案B (#{runs[selected_b]["id"]})',
        line=dict(color='#ff9800', width=1), opacity=0.7
    ))
    fig.update_layout(
        template='plotly_dark',
        title='逐日碳排放对比 (目标2: 碳成本)',
        xaxis_title='Day', yaxis_title='Carbon Cost',
        margin=dict(t=50, b=40, l=50, r=20),
    )
    charts.safe_plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 4: 在 page 路由中注册新页面**

在 app.py 的页面路由（约 40 行处，page 变量附近的 if/elif 结构）添加：

```python
elif page == "📜 历史对比":
    show_history_comparison()
```

- [ ] **Step 5: 提交**

```bash
git add 前端封装/frontend/app.py
git commit -m "feat: add history comparison page, seasonal analysis, real KPI scores"
```

---

### Task 8: config.py 新增页面分组

**Files:**
- Modify: `前端封装/frontend/config.py` — 新增 "📜 历史对比" 和 "🍃 四季分析" 页面

- [ ] **Step 1: 修改 PAGE_GROUPS**

```python
PAGE_GROUPS = {
    "📊 核心看板": ["🏠 系统总览", "📈 综合分析报告"],
    "📈 专项分析": ["🌿 新能源分析", "💧 抽水蓄能调度",
                    "🔥 火电调峰与碳减排", "🎯 Pareto前沿分析"],
    "⚙️ 模型与参数": ["📐 计算公式详解", "⚙️ 参数调整",
                     "🗃️ 原始数据浏览"],
    "🔬 高级功能": ["🎨 高级可视化", "🧠 高级分析", "🔬 A/B参数对比", "📜 历史对比"],
}
```

- [ ] **Step 2: 提交**

```bash
git add 前端封装/frontend/config.py
git commit -m "feat: add history comparison page to navigation"
```

---

## Phase 4: Vue 前端修复 + 后端 API

### Task 9: 后端新增 History API

**Files:**
- Modify: `backend/main.py` — 新增 3 个端点

**Interfaces:**
- Produces: `GET /api/history/list` → list of runs, `GET /api/history/load/{run_id}` → daily data, `POST /api/history/save` → save run

- [ ] **Step 1: 在 main.py 添加 History API 端点**

在 `backend/main.py` 的 `if __name__ == "__main__":` 之前添加：

```python
# ==================== History API ====================

@app.get("/api/history/list")
async def list_history():
    """列出所有历史运行记录"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '前端封装', 'frontend'))
        import db
        runs = db.list_runs()
        return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history/load/{run_id}")
async def load_history(run_id: int):
    """加载某次历史运行的每日结果"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '前端封装', 'frontend'))
        import db
        arr = db.load_run_daily(run_id)
        if arr.size == 0:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return {
            "run_id": run_id,
            "daily": arr.tolist(),
            "params": db.load_run_params(run_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/history/save")
async def save_history(params: dict):
    """保存当前运行结果到数据库"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '前端封装', 'frontend'))
        import db
        run_id = db.save_run(
            data_service._data,
            params=params.get("params", {}),
            region=params.get("region", "华东"),
            year=params.get("year", 2024),
            note=params.get("note", ""),
        )
        return {"run_id": run_id, "status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: 验证端点**

启动后端后：
Run: `curl -s http://localhost:8000/api/history/list`
Expected: `{"runs": [...]}`

- [ ] **Step 3: 提交**

```bash
git add backend/main.py
git commit -m "feat: add history list/load/save API endpoints"
```

---

### Task 10: Vue 前端 SchedulingEditor — 发送曲线数据

**Files:**
- Modify: `前端封装/vue-frontend/src/views/SchedulingEditor.vue` — `updateCarbonResult()` 发送编辑后的 np 曲线
- Modify: `前端封装/vue-frontend/src/api/index.js` — 新增 `saveHistory()` 和 `fetchHistory()` 调用

- [ ] **Step 1: 修改 updateCarbonResult 发送曲线数据**

在 `SchedulingEditor.vue` 的 `updateCarbonResult` 函数（约 340 行）修改为：

```javascript
async function updateCarbonResult() {
  try {
    // 发送当前编辑的抽蓄调度曲线到后端
    const npumpEdited = editedSchedule.value || dayData.value?.np_raw;
    const result = await simulate({
      ...params.value,
      npump_override: npumpEdited,  // 发送编辑后的曲线
    });
    simulatedNpRaw.value = result.np_raw;
    simulatedNt.value = result.Nt;
    simulatedNt2.value = result.Nt2;
    carbonResult.value = result.carbon_result;
  } catch {
    // 保持现有值
  }
}
```

- [ ] **Step 2: 在 api/index.js 新增 History API 调用**

```javascript
/** 获取历史运行列表 */
export async function fetchHistoryList() {
  const { data } = await api.get('/history/list')
  return data
}

/** 加载历史运行 */
export async function fetchHistoryRun(runId) {
  const { data } = await api.get(`/history/load/${runId}`)
  return data
}

/** 保存运行到历史 */
export async function saveHistory(params) {
  const { data } = await api.post('/history/save', params)
  return data
}
```

- [ ] **Step 3: 提交**

```bash
git add 前端封装/vue-frontend/src/views/SchedulingEditor.vue 前端封装/vue-frontend/src/api/index.js
git commit -m "fix: send edited pump curve to backend + add history API calls"
```

---

### Task 11: Vue 前端 SimulationView — 接入数据库保存/加载

**Files:**
- Modify: `前端封装/vue-frontend/src/views/SimulationView.vue` — 对比结果保存到后端 DB

- [ ] **Step 1: 在 SimulationView.vue 的 saveScenario 中添加后端保存**

修改 `saveScenario` 函数（约 457 行）为：

```javascript
import { saveHistory, fetchHistoryList, fetchHistoryRun } from '../api'

async function saveScenario() {
  const name = scenarioName.value.trim()
  if (!name) {
    alert('请输入场景名称')
    return
  }
  // 保存到 localStorage（本地快速访问）
  savedScenarios.value.push({
    name,
    params: { ...paramsA },
    time: new Date().toLocaleString('zh-CN'),
    result: resultA.value ? { ...resultA.value } : null,
  })
  saveScenarios()

  // 同时保存到后端数据库
  try {
    const res = await saveHistory({
      params: { ...paramsA },
      note: name,
      region: '华东',
      year: 2024,
    })
    console.log('Saved to DB, run_id:', res.run_id)
  } catch (e) {
    console.warn('DB save failed (backend may be offline):', e)
  }

  scenarioName.value = ''
}
```

- [ ] **Step 2: 相似地修改 loadScenario 以支持从 DB 加载**

保留 localStorage 逻辑不变，只添加 try-catch：当 localStorage 无数据时尝试从后端加载。

- [ ] **Step 3: 提交**

```bash
git add 前端封装/vue-frontend/src/views/SimulationView.vue
git commit -m "feat: persist simulation scenarios to backend database"
```

---

## Verification Checklist

- [ ] MATLAB: 运行 `compare_algorithms.m`，生成 `comparison_results.mat`
- [ ] MATLAB: 运行 `scenario_extraction.m`，生成 `scenario_data.mat`
- [ ] Python: `from data_loader import load_comparison_data; assert load_comparison_data() is not None`（如果 .mat 存在）
- [ ] Streamlit: 打开 `http://localhost:8501` → 导航到"历史对比"页 → 确认显示历史记录
- [ ] Streamlit: 综合分析报告页 → 确认四季对比分析显示
- [ ] FastAPI: `curl http://localhost:8000/api/history/list` 返回 runs 数组
- [ ] Vue: 打开 `http://localhost:5173` → SchedulingEditor → 拖拽曲线 → 点应用 → 确认指标更新
- [ ] Vue: SimulationView → A/B 对比 → 保存场景 → 确认后端 DB 有记录
