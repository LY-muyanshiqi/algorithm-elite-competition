% rigorous_compare.m - 严谨的 Q-Learning vs 固定对比（多天×多重复×有方差）
% 结果存 rigorous_results.mat，供 Python 统计检验
clear;

Nh = load('ningxia_hydro.txt'); Nw = load('ningxia_wind.txt');
Np = load('ningxia_solar.txt'); L = load('ningxia_fh.txt');
Zpump = 600;

days = [1, 90, 180, 270, 360];
pop_size = 50;
n_gen = 300;
n_runs = 10;

fprintf('=== 严谨对比: Q-Learning vs Fixed (宁夏, %d天, gen=%d, %d次) ===\n', ...
    length(days), n_gen, n_runs);

% 存储结构: results(d).(config).f1_min / f2_min，各 n_runs x 1
results = struct();

for d = 1:length(days)
    day = days(d);
    fprintf('\n--- Day %d (%d/%d) ---\n', day, d, length(days));
    for c = 1:2
        if c == 1, cname = 'fixed'; else, cname = 'qlearning'; end
        f1_mins = zeros(n_runs, 1);
        f2_mins = zeros(n_runs, 1);
        for r = 1:n_runs
            rng(day*10000 + c*1000 + r);
            options = struct('pop', pop_size, 'gen', n_gen, 'init_method', 'logistic', 'track_hv', false);
            if c == 1
                options.op_probs = [0.4, 0, 0, 0, 0, 0.3, 0.3];
            else
                options.use_qlearning = true; options.track_strategy = true;
            end
            [chromosome, ~] = nslde_enhanced(Nh(day,:), Nw(day,:), Np(day,:), L(day,:), Zpump, 4, 0.05, options);
            f1 = chromosome(:, 24); f2 = chromosome(:, 25);
            fea = ~isinf(f1) & ~isinf(f2);
            f1_mins(r) = min(f1(fea));
            f2_mins(r) = min(f2(fea));
        end
        results(d).(cname).f1_min = f1_mins;
        results(d).(cname).f2_min = f2_mins;
        fprintf('  %s: f1 mean=%.1f std=%.1f | f2 mean=%.3e\n', cname, mean(f1_mins), std(f1_mins), mean(f2_mins));
    end
end

save('rigorous_results.mat', 'results', 'days', 'pop_size', 'n_gen', 'n_runs');
fprintf('\n结果已存 rigorous_results.mat\n');
