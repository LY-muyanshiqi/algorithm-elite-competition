% ablation_rigorous.m - 四省三机制消融(严谨版)
clear;
provinces = {'shaanxi','gansu','qinghai','ningxia'};
Zpump_map = [1400, 1400, 800, 600];
pop = 60; gen = 500; n_runs = 10;
days = [1, 90, 180, 270, 360];  % 5个代表日

configs = {
    'E0_nomech',    'random',   [0,0,0,0.5,0.5,0,0];
    'E1_chaos',     'logistic', [0,0,0,0.5,0.5,0,0];
    'E2_chaosDE',   'logistic', [0.5,0,0,0,0.5,0,0];
    'E3_full',      'logistic', [0.4,0,0,0,0,0.3,0.3];
};

results = struct();

for p = 1:length(provinces)
    prov = provinces{p};
    Z = Zpump_map(p);
    % 加载数据
    if strcmp(prov, 'shaanxi')
        NH = load('hydro.txt'); NW = load('wind.txt'); NP = load('solar.txt'); L = load('FH.txt');
    else
        NH = load([prov '_hydro.txt']); NW = load([prov '_wind.txt']);
        NP = load([prov '_solar.txt']); L = load([prov '_fh.txt']);
    end
    fprintf('\n===== %s (Zpump=%d) =====\n', prov, Z);
    for c = 1:size(configs,1)
        cname = configs{c,1}; init = configs{c,2}; op = configs{c,3};
        f1_all = []; f2_all = [];
        for d = 1:length(days)
            day = days(d);
            for r = 1:n_runs
                rng(p*100000 + c*10000 + d*100 + r);
                options = struct('pop',pop,'gen',gen,'init_method',init,'track_hv',false,'op_probs',op);
                chr = nslde_enhanced(NH(day,:),NW(day,:),NP(day,:),L(day,:),Z,4,0.05,options);
                f1=chr(:,24); f2=chr(:,25);
                fea=isfinite(f1)&isfinite(f2);
                if any(fea)
                    f1_all(end+1) = min(f1(fea));
                    f2_all(end+1) = min(f2(fea));
                end
            end
        end
        results.(prov).(cname).f1 = f1_all;
        finite_f1 = f1_all(isfinite(f1_all));
        if isempty(finite_f1)
            f1_mean = Inf;
            f1_std = 0;
        else
            f1_mean = mean(finite_f1);
            f1_std = std(finite_f1);
        end
        fprintf('  %-12s: f1 mean=%.1f std=%.1f (n=%d)\n', cname, f1_mean, f1_std, length(finite_f1));
    end
end
save('ablation_rigorous.mat', 'results', 'provinces', 'Zpump_map', 'configs', 'days', 'n_runs', 'pop', 'gen');
fprintf('\n结果已存 ablation_rigorous.mat\n');
