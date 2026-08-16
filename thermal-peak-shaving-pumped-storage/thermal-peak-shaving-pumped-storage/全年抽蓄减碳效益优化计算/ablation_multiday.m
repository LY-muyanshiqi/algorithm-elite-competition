% 多天验证三机制消融的稳定性
clear;
Nh = load('ningxia_hydro.txt'); Nw = load('ningxia_wind.txt');
Np = load('ningxia_solar.txt'); L = load('ningxia_fh.txt');
Zpump = 600;
pop_size = 50; n_gen = 100; n_runs = 10;
days = [1, 90, 180, 270, 360];

configs = {
    'E0_nomech',    'random',   [0,0,0,0.5,0.5,0,0];
    'E1_chaos',     'logistic', [0,0,0,0.5,0.5,0,0];
    'E2_chaos_DE',  'logistic', [0.5,0,0,0,0.5,0,0];
    'E3_full',      'logistic', [0.4,0,0,0,0,0.3,0.3];
};

fprintf('=== 多天三机制消融 (宁夏 %d天) ===\n', length(days));
for d = 1:length(days)
    day = days(d);
    line = sprintf('Day %3d:', day);
    for c = 1:size(configs,1)
        cname = configs{c,1}; init = configs{c,2}; op = configs{c,3};
        f1s = zeros(n_runs,1);
        for r = 1:n_runs
            rng(day*10000 + c*1000 + r);
            options = struct('pop',pop_size,'gen',n_gen,'init_method',init,'track_hv',false,'op_probs',op);
            chr = nslde_enhanced(Nh(day,:),Nw(day,:),Np(day,:),L(day,:),Zpump,4,0.05,options);
            f1 = chr(:,24); f2 = chr(:,25); fea = ~isinf(f1)&~isinf(f2);
            if any(fea), f1s(r) = min(f1(fea)); else, f1s(r) = nan; end
        end
        line = sprintf('%s  %s=%.0f', line, cname, nanmean(f1s));
    end
    fprintf('%s\n', line);
end
