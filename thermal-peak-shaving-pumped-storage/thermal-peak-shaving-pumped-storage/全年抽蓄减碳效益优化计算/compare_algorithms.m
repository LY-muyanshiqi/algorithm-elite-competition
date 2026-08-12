% compare_algorithms.m - 多算法对比实验脚本 v2.0
% 选取 5 个代表日运行 NSLDE / NSGA-II / NSGA-III / MOEA/D / MOEA/D-DE
% 保存结果到 .mat 文件
clear; clc;

data_dir = '../前端封装/frontend/';

NH = load('hydro.txt');
NW = load('wind.txt');
NP = load('solar.txt');
FH = load('FH.txt');
N = length(NH(:, 1));

Zpump = 1400;
h = 4;
Cprice = [40 40 40 40 40 40 50 60 80 90 90 80 ...
          70 70 80 90 100 100 90 80 60 50 40 40] / 1000;

fh_mean = mean(FH, 2);

season_ranges = {1:90, 91:181, 182:273, 274:365};
typical_days = zeros(1, 4);
for s = 1:4
    days = season_ranges{s};
    season_mean = mean(fh_mean(days));
    [~, idx] = min(abs(fh_mean(days) - season_mean));
    typical_days(s) = days(idx);
end

[~, max_load_day] = max(fh_mean);

days_to_run = [typical_days, max_load_day];
n_days = length(days_to_run);

algorithm_names = {'NSLDE', 'NSGA-II', 'NSGA-III', 'MOEA/D', 'MOEA/D-DE'};
n_algs = length(algorithm_names);

fprintf('=== Multi-Algorithm Benchmark ===\n');
fprintf('Algorithms: %s\n', strjoin(algorithm_names, ', '));
fprintf('Days (%d): %s\n', n_days, mat2str(days_to_run));

z_all = zeros(n_days, 100, 2, n_algs);
hv = zeros(n_days, n_algs);
igd = zeros(n_days, n_algs);
spacing = zeros(n_days, n_algs);
timing = zeros(n_days, n_algs);

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
    A = nslde(Nh, Nw, Np, L, Zpump, h, Cprice);
    timing(d_idx, 1) = toc;
    z_all(d_idx, :, :, 1) = A(:, 24:25);
    fprintf('  NSLDE:      %.1fs\n', timing(d_idx, 1));

    % NSGA-II
    tic;
    A = nsga2_standard(Nh, Nw, Np, L, Zpump, h, Cprice);
    timing(d_idx, 2) = toc;
    z_all(d_idx, :, :, 2) = A(:, 24:25);
    fprintf('  NSGA-II:    %.1fs\n', timing(d_idx, 2));

    % NSGA-III
    tic;
    A = nsga3_standard(Nh, Nw, Np, L, Zpump, h, Cprice);
    timing(d_idx, 3) = toc;
    z_all(d_idx, :, :, 3) = A(:, 24:25);
    fprintf('  NSGA-III:   %.1fs\n', timing(d_idx, 3));

    % MOEA/D
    tic;
    A = moead_standard(Nh, Nw, Np, L, Zpump, h, Cprice);
    timing(d_idx, 4) = toc;
    z_all(d_idx, :, :, 4) = A(:, 24:25);
    fprintf('  MOEA/D:     %.1fs\n', timing(d_idx, 4));

    % MOEA/D-DE
    tic;
    A = moead_de(Nh, Nw, Np, L, Zpump, h, Cprice);
    timing(d_idx, 5) = toc;
    z_all(d_idx, :, :, 5) = A(:, 24:25);
    fprintf('  MOEA/D-DE:  %.1fs\n', timing(d_idx, 5));

    % Compute metrics
    ref_point = [0, 0];
    for alg = 1:n_algs
        ref_point(1) = max(ref_point(1), max(z_all(d_idx, :, 1, alg)) * 1.1);
        ref_point(2) = max(ref_point(2), max(z_all(d_idx, :, 2, alg)) * 1.1);
    end

    for alg = 1:n_algs
        hv(d_idx, alg) = compute_hv(squeeze(z_all(d_idx, :, :, alg)), ref_point);
        spacing(d_idx, alg) = compute_spacing(squeeze(z_all(d_idx, :, :, alg)));
    end
    for alg = 2:n_algs
        igd(d_idx, alg) = compute_igd(squeeze(z_all(d_idx, :, :, 1)), squeeze(z_all(d_idx, :, :, alg)));
    end
end

% Save results
z_nslde = z_all(:, :, :, 1);
z_nsga2 = z_all(:, :, :, 2);
z_nsga3 = z_all(:, :, :, 3);
z_moead = z_all(:, :, :, 4);
z_moead_de = z_all(:, :, :, 5);

save(fullfile(data_dir, 'comparison_results.mat'), ...
     'z_nslde', 'z_nsga2', 'z_nsga3', 'z_moead', 'z_moead_de', ...
     'hv', 'igd', 'spacing', 'timing', 'days_to_run', 'algorithm_names');

fprintf('\nResults saved to comparison_results.mat\n');
fprintf('Days: %s\n', mat2str(days_to_run));
for alg = 1:n_algs
    fprintf('%-12s | HV avg: %.2f | Spacing avg: %.4f | Time avg: %.1fs\n', ...
        algorithm_names{alg}, mean(hv(:, alg)), mean(spacing(:, alg)), mean(timing(:, alg)));
end

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
