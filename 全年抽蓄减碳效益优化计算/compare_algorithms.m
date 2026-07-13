% compare_algorithms.m - 三算法对比实验脚本
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
fh_mean = mean(FH, 2);
wind_mean = mean(NW, 2);
solar_mean = mean(NP, 2);

% 四季典型日
season_ranges = {1:90, 91:181, 182:273, 274:365};
typical_days = zeros(1, 4);
for s = 1:4
    days = season_ranges{s};
    season_mean = mean(fh_mean(days));
    [~, idx] = min(abs(fh_mean(days) - season_mean));
    typical_days(s) = days(idx);
end

% 最大负荷日
[~, max_load_day] = max(fh_mean);

days_to_run = [typical_days, max_load_day];
n_days = length(days_to_run);

fprintf('对比实验将运行 %d 天: %s\n', n_days, mat2str(days_to_run));

% === 初始化输出 ===
z_nslde = zeros(n_days, 100, 2);
z_nsga2 = zeros(n_days, 100, 2);
z_moead = zeros(n_days, 100, 2);
hv = zeros(n_days, 3);
igd = zeros(n_days, 3);
spacing = zeros(n_days, 3);
timing = zeros(n_days, 3);

% === 逐日运行 ===
pool = gcp('nocreate');
if isempty(pool)
    parpool('local', 8);
end

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
     'hv', 'igd', 'spacing', 'timing', 'days_to_run');

fprintf('\n结果已保存到 comparison_results.mat\n');
fprintf('Days: %s\n', mat2str(days_to_run));
fprintf('HV (avg) - NSLDE: %.2f  NSGA-II: %.2f  MOEA/D: %.2f\n', mean(hv(:,1)), mean(hv(:,2)), mean(hv(:,3)));
fprintf('IGD (avg) - NSGA-II: %.4f  MOEA/D: %.4f\n', mean(igd(:,2)), mean(igd(:,3)));

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
