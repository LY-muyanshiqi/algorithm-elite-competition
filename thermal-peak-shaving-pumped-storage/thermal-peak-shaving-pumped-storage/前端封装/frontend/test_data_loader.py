"""
Unit tests for data_loader.py core calculation functions.
Run with: python -m pytest test_data_loader.py -v
"""
import numpy as np
import pytest
from data_loader import (
    calculate_npump, compute_cc_from_C, calculate_carbon_reduction,
    calculate_pumped_storage_schedule, recalculate_with_parameters
)


# --- Helpers ---

def _make_365(data_1d):
    """Repeat a 1-day data array to 365 days."""
    return np.tile(data_1d, (365, 1))


# --- Fixtures ---

@pytest.fixture
def mock_data():
    """Create a minimal mock data dict for testing (365 days)."""
    np.random.seed(42)
    return {
        'solution': np.random.uniform(0.2, 0.8, (365, 23)),
        'fh': np.abs(np.random.randn(365, 24) * 200 + 800),
        'hydro': np.abs(np.random.randn(365, 24) * 100 + 300),
        'wind': np.abs(np.random.randn(365, 24) * 150 + 400),
        'solar': np.abs(np.random.randn(365, 24) * 100 + 200),
    }


# --- calculate_npump ---

class TestCalculateNpump:
    def test_returns_tuple(self, mock_data):
        result = calculate_npump(mock_data)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_npump_shape(self, mock_data):
        Npump, C_all = calculate_npump(mock_data)
        assert Npump.shape == (365, 24)
        assert C_all.shape == (365, 25)

    def test_c_all_starts_with_0_5(self, mock_data):
        _, C_all = calculate_npump(mock_data)
        assert np.allclose(C_all[:, 0], 0.5)

    def test_c_all_has_25_columns(self, mock_data):
        """C stores 25 time points per day (C[0] initial + 24 hourly states)."""
        _, C_all = calculate_npump(mock_data)
        assert C_all.shape[1] == 25

    def test_npump_positive_for_generation(self):
        """When solution pushes C down, hours 0-22 should be generating (>= 0).
        Hour 23 may reverse sign to meet the C[24]=0.5 cycle constraint."""
        data = {
            'solution': _make_365(np.full((1, 23), 0.3)),
            'fh': _make_365(np.ones((1, 24)) * 1000),
            'hydro': np.zeros((365, 24)),
            'wind': np.zeros((365, 24)),
            'solar': np.zeros((365, 24)),
        }
        Npump, _ = calculate_npump(data, Zpump=1400, h=4, min_power_ratio=0.2)
        assert np.all(Npump[:, :23] >= 0)

    def test_npump_negative_for_pumping(self):
        """When solution pushes C up, hours 0-22 should be pumping (<= 0).
        Hour 23 may reverse sign to meet the C[24]=0.5 cycle constraint."""
        data = {
            'solution': _make_365(np.full((1, 23), 0.8)),
            'fh': _make_365(np.ones((1, 24)) * 1000),
            'hydro': np.zeros((365, 24)),
            'wind': np.zeros((365, 24)),
            'solar': np.zeros((365, 24)),
        }
        Npump, _ = calculate_npump(data, Zpump=1400, h=4, min_power_ratio=0.2)
        assert np.all(Npump[:, :23] <= 0)

    def test_min_power_ratio_clamps_to_zero(self):
        """Very small C differences should be zeroed out."""
        data = {
            'solution': _make_365(np.full((1, 23), 0.499)),
            'fh': _make_365(np.ones((1, 24)) * 1000),
            'hydro': np.zeros((365, 24)),
            'wind': np.zeros((365, 24)),
            'solar': np.zeros((365, 24)),
        }
        Npump, _ = calculate_npump(data, Zpump=1400, h=4, min_power_ratio=0.2)
        # With diff=0.001*5600=5.6MW < 280MW min, all should be zero
        assert np.allclose(Npump, 0)

    def test_custom_parameters_work(self, mock_data):
        Npump1, _ = calculate_npump(mock_data, Zpump=1400)
        Npump2, _ = calculate_npump(mock_data, Zpump=2000)
        assert not np.allclose(Npump1, Npump2)


# --- compute_cc_from_C ---

class TestComputeCcFromC:
    def test_cc_length(self, mock_data):
        _, C_all = calculate_npump(mock_data)
        cc = compute_cc_from_C(C_all)
        assert len(cc) == 365 * 24 + 1  # 8760 + 1

    def test_cc_starts_with_0_5(self, mock_data):
        _, C_all = calculate_npump(mock_data)
        cc = compute_cc_from_C(C_all)
        assert cc[0] == 0.5

    def test_cc_values_in_range(self, mock_data):
        _, C_all = calculate_npump(mock_data)
        cc = compute_cc_from_C(C_all)
        assert cc.min() >= 0.0
        assert cc.max() <= 1.0


# --- calculate_carbon_reduction ---

class TestCalculateCarbonReduction:
    def test_returns_dict_with_expected_keys(self, mock_data):
        result = calculate_carbon_reduction(mock_data)
        for key in ['power_change', 'carbon_change', 'daily_carbon_change', 'Nt', 'Nt2']:
            assert key in result

    def test_nt_and_nt2_same_shape(self, mock_data):
        result = calculate_carbon_reduction(mock_data)
        assert result['Nt'].shape == (365, 24)
        assert result['Nt2'].shape == (365, 24)

    def test_power_change_is_scalar(self, mock_data):
        result = calculate_carbon_reduction(mock_data)
        assert np.isscalar(result['power_change'])

    def test_daily_carbon_change_length(self, mock_data):
        result = calculate_carbon_reduction(mock_data)
        assert len(result['daily_carbon_change']) == 365

    def test_carbon_factor_scales_result(self, mock_data):
        """Higher carbon factor should produce proportionally larger carbon_change."""
        r1 = calculate_carbon_reduction(mock_data, carbon_factor=0.5)
        r2 = calculate_carbon_reduction(mock_data, carbon_factor=1.0)
        # r2 should be exactly 2x r1 (same sign, different magnitude)
        assert r1['carbon_change'] * 2 == pytest.approx(r2['carbon_change'])


# --- calculate_pumped_storage_schedule ---

class TestCalculatePumpedStorageSchedule:
    def test_returns_dict_with_expected_keys(self):
        np_power = np.random.randn(365, 24) * 500
        stats = calculate_pumped_storage_schedule(np_power)
        for key in ['generating_hours', 'pumping_hours', 'idle_hours',
                     'total_generation', 'total_pumping', 'efficiency']:
            assert key in stats

    def test_hours_sum_to_total(self):
        np_power = np.random.randn(365, 24) * 500
        stats = calculate_pumped_storage_schedule(np_power)
        assert stats['generating_hours'] + stats['pumping_hours'] + stats['idle_hours'] == 365 * 24

    def test_efficiency_is_finite(self):
        """Efficiency should be a finite number; may exceed 100% for nonsense input."""
        np_power = np.random.randn(365, 24) * 500
        stats = calculate_pumped_storage_schedule(np_power)
        assert np.isfinite(stats['efficiency'])


# --- recalculate_with_parameters ---

class TestRecalculateWithParameters:
    def test_returns_dict_with_expected_keys(self, mock_data):
        result = recalculate_with_parameters(mock_data, {})
        for key in ['np_raw', 'Nt', 'Nt2', 'cc', 'carbon_result', 'ps_stats', 'params']:
            assert key in result

    def test_np_raw_shape(self, mock_data):
        result = recalculate_with_parameters(mock_data, {})
        assert result['np_raw'].shape == (365, 24)

    def test_cc_length(self, mock_data):
        result = recalculate_with_parameters(mock_data, {})
        assert len(result['cc']) == 365 * 24 + 1

    def test_different_params_give_different_results(self, mock_data):
        r1 = recalculate_with_parameters(mock_data, {'Zpump': 1000, 'h': 4, 'efficiency': 0.75, 'min_power_ratio': 0.2})
        r2 = recalculate_with_parameters(mock_data, {'Zpump': 3000, 'h': 8, 'efficiency': 0.9, 'min_power_ratio': 0.1})
        assert not np.allclose(r1['np_raw'], r2['np_raw'])
