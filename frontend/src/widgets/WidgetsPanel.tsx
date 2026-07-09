import HeatRiskIndexWidget from './HeatRiskIndexWidget';
import SatellitePassWidget from './SatellitePassWidget';
import LatestLSTAcquisitionWidget from './LatestLSTAcquisitionWidget';
import AIConfidenceScoreWidget from './AIConfidenceScoreWidget';
import HeatwaveTrendWidget from './HeatwaveTrendWidget';
import VegetationRecoveryWidget from './VegetationRecoveryWidget';
import RiskForecastWidget from './RiskForecastWidget';
import RecommendedActionsWidget from './RecommendedActionsWidget';

export default function WidgetsPanel() {
  return (
    <div className="space-y-6">
      <HeatRiskIndexWidget />
      <SatellitePassWidget />
      <LatestLSTAcquisitionWidget />
      <AIConfidenceScoreWidget />
      <HeatwaveTrendWidget />
      <VegetationRecoveryWidget />
      <RiskForecastWidget />
      <RecommendedActionsWidget />
    </div>
  );
}