function [H, e, g, Ce1, Ce2, Ce3] = carbon_intensity_continuous(load_ratio)
% carbon_intensity_continuous - continuous carbon emission model via pchip
%
% Replaces the three-segment step model in evaluate_objective.m and tanpafangjisuan.m.
%
% Improvement:
%   Old model: hard discontinuity at 30%/50% load, coal rate 300->330->370 g/kWh
%   New model: pchip (shape-preserving piecewise cubic Hermite) smooth continuous curve
%
% Input:
%   load_ratio - thermal load ratio (0~1), scalar or vector
%
% Output:
%   H   - supply coal consumption (g/kWh), continuous
%   e   - combustion efficiency
%   g   - turbine mechanical efficiency
%   Ce1 - base carbon emission intensity (gCO2/kWh)
%   Ce2 - efficiency-loss carbon emission intensity
%   Ce3 - auxiliary process carbon emission intensity
%
% Data source: measured parameters at 4 operating points
%   Operating points: 30% -> 40% -> 50% -> 100% load
%   Coal:    370     -> 330     -> 300     -> 300 g/kWh
%   Combustion eff: 0.904 -> 0.920 -> 0.934 -> 0.953
%   Mechanical eff: 0.401 -> 0.424 -> 0.442 -> 0.458

    % Operating point definitions
    load_points = [0.30, 0.40, 0.50, 1.00];
    H_points    = [370,  330,  300,  300];
    e_points    = [0.904, 0.920, 0.934, 0.953];
    g_points    = [0.401, 0.424, 0.442, 0.458];

    % pchip shape-preserving interpolation - monotonic, no overshoot
    if isscalar(load_ratio)
        H = pchip(load_points, H_points, max(load_ratio, 0.30));
        e = pchip(load_points, e_points, max(load_ratio, 0.30));
        g = pchip(load_points, g_points, max(load_ratio, 0.30));
    else
        H = pchip(load_points, H_points, max(load_ratio, 0.30));
        e = pchip(load_points, e_points, max(load_ratio, 0.30));
        g = pchip(load_points, g_points, max(load_ratio, 0.30));
    end

    % Carbon emission parameters
    OF = 0.99;
    Cc = 0.7;
    Mco2 = 44;
    Mc = 12;
    e_100 = 0.953;
    g_100 = 0.458;
    Cq = 0.9183;
    a = 0.02;
    ps = 0.01;
    us = 0.95;
    Ms = 32;
    as_val = 0.0148;
    ys = 0.00392;

    % Base emission
    Ce1 = H .* OF .* Cc .* Mco2 ./ Mc;

    % Efficiency-loss emission
    Ce2 = H .* (1 - e ./ e_100) .* Cq ...
        + H .* (1 - g ./ g_100) .* Cq ...
        + a .* H .* Cq;

    % Auxiliary emission
    Ce3 = H .* ps .* us .* Mco2 ./ Ms ...
        + H .* as_val .* Cq ...
        + H .* ys .* Cq;
end
