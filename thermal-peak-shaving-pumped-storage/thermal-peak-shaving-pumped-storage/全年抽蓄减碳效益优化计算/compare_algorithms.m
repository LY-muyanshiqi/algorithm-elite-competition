% compare_algorithms.m -  v2.0
%  5  NSLDE / NSGA-II / NSGA-III / MOEA/D / MOEA/D-DE
%  .mat 
clear; clc;

data_dir = '..//frontend/';

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

% Missing/short solver outputs must not become artificial zero-objective
% points.  Metric helpers filter these NaN rows explicitly.
z_all = nan(n_days, 100, 2, n_algs);
hv = zeros(n_days, n_algs);
% IGD is undefined when no finite objective/reference points exist.  Keep
% those entries as NaN so downstream aggregation cannot mistake them for a
% perfect score of zero.
igd = nan(n_days, n_algs);
spacing = zeros(n_days, n_algs);
timing = zeros(n_days, n_algs);

% Keep the metric provenance in the MAT file.  The Python robust benchmark
% uses the same definition: a joint non-dominated reference front assembled
% from every algorithm on the same test instance, with both objectives
% normalized by the union range before Euclidean distances are measured.
igd_reference_definition = 'joint non-dominated union front; min-max normalized objectives';

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
    day_points = reshape(z_all(d_idx, :, :, :), [], 2);
    finite_mask = all(isfinite(day_points), 2);
    if any(finite_mask)
        ref_point = max(day_points(finite_mask, :), [], 1) * 1.1;
        union_min = min(day_points(finite_mask, :), [], 1);
        union_span = max(day_points(finite_mask, :), [], 1) - union_min + 1e-12;
        % The IGD reference is independent of the algorithm being scored.
        % This avoids giving NSLDE a privileged zero baseline and matches the
        % common-reference construction in backend/robust_optimization_service.py.
        igd_reference_front = compute_nondominated_front(day_points(finite_mask, :));
    else
        ref_point = [1e5, 1e10];
        union_min = [0, 0];
        union_span = [1, 1];
        igd_reference_front = zeros(0, 2);
    end

    for alg = 1:n_algs
        points = squeeze(z_all(d_idx, :, :, alg));
        hv(d_idx, alg) = compute_hv(points, ref_point);
        spacing(d_idx, alg) = compute_spacing(points);
        % Score every algorithm against the same joint reference front.
        igd(d_idx, alg) = compute_igd(igd_reference_front, points, ...
                                      union_min, union_span);
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
     'hv', 'igd', 'spacing', 'timing', 'days_to_run', 'algorithm_names', ...
     'igd_reference_definition');

fprintf('\nResults saved to comparison_results.mat\n');
fprintf('Days: %s\n', mat2str(days_to_run));
for alg = 1:n_algs
    fprintf(['%-12s | HV avg: %.2f | IGD avg: %.6f | Spacing avg: %.4f | ', ...
             'Time avg: %.1fs\n'], ...
        algorithm_names{alg}, mean(hv(:, alg), 'omitnan'), ...
        mean(igd(:, alg), 'omitnan'), mean(spacing(:, alg)), mean(timing(:, alg)));
end

% ===  ===
function hv = compute_hv(points, ref_point)
    hv = compute_hv_2d(points, ref_point);
end

function hv = compute_hv_2d(points, ref_point)
    if isempty(points), hv = 0; return; end
    points = double(points);
    ref_point = double(ref_point(:)');
    if size(points, 2) ~= 2 || numel(ref_point) ~= 2 || any(~isfinite(ref_point))
        error('points must be N-by-2 and ref_point must contain two finite values');
    end
    points = points(all(isfinite(points), 2), :);
    points = points(points(:, 1) < ref_point(1) & points(:, 2) < ref_point(2), :);
    if isempty(points), hv = 0; return; end
    points = sortrows(points, [1 2]);
    front = zeros(size(points));
    count = 0;
    best_y = inf;
    for i = 1:size(points, 1)
        if points(i, 2) < best_y
            count = count + 1;
            front(count, :) = points(i, :);
            best_y = points(i, 2);
        end
    end
    front = front(1:count, :);
    widths = diff([front(:, 1); ref_point(1)]);
    heights = ref_point(2) - front(:, 2);
    hv = sum(widths .* heights);
end

function front = compute_nondominated_front(points)
    % Return the unique non-dominated subset of a 2-D minimization set.
    % Sorting by f1 then f2 and retaining strictly improving f2 matches the
    % Python _nondominated_points helper used by the robust backend.
    if isempty(points)
        front = zeros(0, 2);
        return;
    end
    points = double(points);
    points = points(all(isfinite(points), 2), :);
    if isempty(points)
        front = zeros(0, 2);
        return;
    end
    points = sortrows(points, [1, 2]);
    keep = false(size(points, 1), 1);
    best_y = inf;
    for i = 1:size(points, 1)
        if points(i, 2) < best_y
            keep(i) = true;
            best_y = points(i, 2);
        end
    end
    front = points(keep, :);
end

function igd = compute_igd(ref, points, scale_min, scale_span)
    % Compute normalized IGD for a minimization problem.
    %
    % ``ref`` must be the common joint reference front.  ``scale_min`` and
    % ``scale_span`` are computed once from the union of all algorithms for a
    % test day, so objective units cannot let one axis dominate the distance.
    % A NaN result denotes an empty/invalid reference or candidate front.
    ref = double(ref);
    points = double(points);
    ref = ref(all(isfinite(ref), 2), :);
    points = points(all(isfinite(points), 2), :);
    if isempty(ref) || isempty(points)
        igd = NaN;
        return;
    end
    if nargin < 3 || isempty(scale_min) || nargin < 4 || isempty(scale_span)
        all_points = [ref; points];
        scale_min = min(all_points, [], 1);
        scale_span = max(all_points, [], 1) - scale_min + 1e-12;
    end
    scale_min = double(reshape(scale_min, 1, []));
    scale_span = double(reshape(scale_span, 1, []));
    if numel(scale_min) ~= 2 || numel(scale_span) ~= 2 || ...
            any(~isfinite(scale_min)) || any(~isfinite(scale_span)) || ...
            any(scale_span <= 0)
        igd = NaN;
        return;
    end

    ref_normalized = (ref - scale_min) ./ scale_span;
    points_normalized = (points - scale_min) ./ scale_span;
    nearest = zeros(size(ref_normalized, 1), 1);
    for i = 1:size(ref_normalized, 1)
        delta = points_normalized - ref_normalized(i, :);
        distances = sqrt(sum(delta .^ 2, 2));
        nearest(i) = min(distances);
    end
    igd = mean(nearest);
end

function s = compute_spacing(points)
    % Match backend._spacing: normalize both objectives to [0, 1], then
    % report the sample standard deviation of nearest-neighbour distances.
    % Filtering invalid rows keeps one failed solver evaluation from making
    % the whole benchmark metric NaN.
    points = double(points);
    if isempty(points) || size(points, 2) ~= 2
        s = 0;
        return;
    end
    points = points(all(isfinite(points), 2), :);
    n = size(points, 1);
    if n <= 2, s = 0; return; end
    lower = min(points, [], 1);
    span = max(points, [], 1) - lower + 1e-12;
    points = (points - lower) ./ span;
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
    % MATLAB std(..., 0) uses the N-1 denominator, matching numpy.std(...,
    % ddof=1) in backend/robust_optimization_service.py.
    s = std(dists, 0);
end
