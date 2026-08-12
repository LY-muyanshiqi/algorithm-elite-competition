% scenario_extraction.m - 
% 365 + 6 + 24h
clear; clc;

%  AA.mat
data_dir = '..//frontend/';
load(fullfile(data_dir, 'AA.mat'));       % AA: (365, 23) 
NH = load('hydro.txt');
NW = load('wind.txt');
NP = load('solar.txt');
FH = load('FH.txt');

N = 365;
solution = AA(:, 1:23);
z_gain = AA(:, 24:25);
Zpump = 1400;
h = 4;

% === 1.  ===
fh_mean = mean(FH, 2);
wind_mean = mean(NW, 2);
solar_mean = mean(NP, 2);

% 
[~, max_load_day] = max(fh_mean);
[~, min_load_day] = min(fh_mean);

% 
[~, max_wind_day] = max(wind_mean);
[~, min_wind_day] = min(wind_mean);
[~, max_solar_day] = max(solar_mean);

% 
daily_range = max(FH, [], 2) - min(FH, [], 2);
[~, max_range_day] = max(daily_range);

% ---  ---
season_ranges = {1:90, 91:181, 182:273, 274:365};
season_names = {'Spring', 'Summer', 'Autumn', 'Winter'};
typical_days = zeros(1, 4);

for s = 1:4
    days = season_ranges{s};
    season_mean = mean(fh_mean(days));
    [~, idx] = min(abs(fh_mean(days) - season_mean));
    typical_days(s) = days(idx);
end

% === 2. 24h ===
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

for i = 1:n_scenarios
    name = scenario_defs{i, 1};
    day = scenario_defs{i, 2};

    % 24h
    sc.hydro = NH(day, :);
    sc.wind = NW(day, :);
    sc.solar = NP(day, :);
    sc.load = FH(day, :);
    sc.solution = solution(day, :);
    sc.z1 = z_gain(day, 1);
    sc.z2 = z_gain(day, 2);
    sc.day_index = day;

    %  Npump (24h)
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

% ===  ===
save(fullfile(data_dir, 'scenario_data.mat'), '-struct', 'scenario_data');
fprintf('\n scenario_data.mat\n');
