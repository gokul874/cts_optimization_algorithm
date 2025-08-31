import pandas as pd
import numpy as np
import logging
from collections import defaultdict
from sklearn.neighbors import BallTree

logger = logging.getLogger(__name__)

class NetworkOptimizer:
    """Handles provider network optimization and assignment logic (BallTree-backed)."""
    
    def __init__(self):
        # kept the same key terms / values as requested
        self.optimization_weights = {
            'rating': 0.5,    # Higher weight for rating
            'cost': 0.3,      # Medium weight for cost (lower is better)
            'distance': 0.2   # Lower weight for distance (shorter is better)
        }
        # Earth radius in kilometers for haversine conversions
        self._earth_radius_km = 6371.0

        # cost reduction bounds (constraint)
        self.cost_reduction_bounds = (8.0, 12.0)  # percentage

    def calculate_provider_score(self, rating, cost, distance):
        """Calculate optimization score for a provider. Higher score is better."""
        try:
            rating_score = rating / 5.0
            max_cost = 1000  # assume max reasonable cost
            cost_score = max(0, (max_cost - cost) / max_cost)
            max_distance = 15.0
            distance_score = max(0, (max_distance - distance) / max_distance)

            total_score = (
                rating_score * self.optimization_weights['rating'] +
                cost_score * self.optimization_weights['cost'] +
                distance_score * self.optimization_weights['distance']
            )

            return total_score

        except Exception as e:
            logger.warning(f"Error calculating provider score: {str(e)}")
            return 0.0

    def find_best_provider(self, member_candidates):
        """Pick the best provider (rating > cost > distance)."""
        if not member_candidates:
            return None

        try:
            candidates_df = pd.DataFrame(member_candidates)

            max_rating = candidates_df['rating'].max()
            highest_rated = candidates_df[candidates_df['rating'] == max_rating]

            if len(highest_rated) == 1:
                return highest_rated.iloc[0].to_dict()

            min_cost = highest_rated['cost'].min()
            lowest_cost = highest_rated[highest_rated['cost'] == min_cost]

            if len(lowest_cost) == 1:
                return lowest_cost.iloc[0].to_dict()

            min_distance = lowest_cost['distance'].min()
            best_provider = lowest_cost[lowest_cost['distance'] == min_distance].iloc[0]

            return best_provider.to_dict()

        except Exception as e:
            logger.error(f"Error finding best provider: {str(e)}")
            return None

    def find_candidate_connections(self, members_df, providers_df, geospatial=None, max_distance=15.0):
        """Use BallTree to find providers within radius."""
        candidate_connections = []

        try:
            logger.info(f"Processing {len(members_df)} members against {len(providers_df)} providers")

            if 'Latitude' not in members_df.columns or 'Longitude' not in members_df.columns:
                raise ValueError("members_df must contain 'Latitude' and 'Longitude'")
            if 'Latitude' not in providers_df.columns or 'Longitude' not in providers_df.columns:
                raise ValueError("providers_df must contain 'Latitude' and 'Longitude'")

            providers_df = providers_df.copy()
            providers_df['Latitude'] = pd.to_numeric(providers_df['Latitude'], errors='coerce')
            providers_df['Longitude'] = pd.to_numeric(providers_df['Longitude'], errors='coerce')

            valid_providers_mask = providers_df['Latitude'].notna() & providers_df['Longitude'].notna()
            providers_valid = providers_df[valid_providers_mask].reset_index(drop=True)

            if providers_valid.empty:
                return []

            provider_coords_rad = np.radians(providers_valid[['Latitude', 'Longitude']].values)
            tree = BallTree(provider_coords_rad, metric='haversine')

            radius_radians = max_distance / self._earth_radius_km

            batch_size = 100
            members_df = members_df.copy()
            members_df['Latitude'] = pd.to_numeric(members_df['Latitude'], errors='coerce')
            members_df['Longitude'] = pd.to_numeric(members_df['Longitude'], errors='coerce')

            for i in range(0, len(members_df), batch_size):
                batch_end = min(i + batch_size, len(members_df))
                members_batch = members_df.iloc[i:batch_end]

                member_coords_list = []
                member_indices = []
                for idx, member in members_batch.iterrows():
                    if pd.isna(member['Latitude']) or pd.isna(member['Longitude']):
                        continue
                    member_coords_list.append([member['Latitude'], member['Longitude']])
                    member_indices.append(idx)

                if not member_coords_list:
                    continue

                member_coords_rad = np.radians(np.array(member_coords_list))
                indices_array = tree.query_radius(member_coords_rad, r=radius_radians, return_distance=False)

                for list_idx, provider_idxs in enumerate(indices_array):
                    member_idx = member_indices[list_idx]
                    member = members_df.loc[member_idx]
                    member_lat = member['Latitude']
                    member_lon = member['Longitude']
                    member_source_type = member.get('SourceType', '')
                    member_id = member.get('MemberID')

                    if len(provider_idxs) == 0:
                        continue

                    matched_providers = providers_valid.iloc[provider_idxs].copy().reset_index(drop=True)
                    mem_rad = np.radians([member_lat, member_lon])
                    prov_rad = np.radians(matched_providers[['Latitude', 'Longitude']].values)

                    lat1 = mem_rad[0]
                    lon1 = mem_rad[1]
                    lat2 = prov_rad[:, 0]
                    lon2 = prov_rad[:, 1]

                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
                    great_circle_radians = 2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
                    distances_km = great_circle_radians * self._earth_radius_km

                    matched_providers = matched_providers.assign(distance_km=distances_km)

                    for _, provider in matched_providers.iterrows():
                        provider_type = provider.get('Type', '')
                        provider_source = provider.get('Source', '')

                        type_match = False
                        if member_source_type == 'Supply Directory' and 'Supplier Directory' in str(provider_source):
                            type_match = True
                        elif member_source_type in ['Hospital', 'Nursing Home', 'Scan Center']:
                            type_match = len(str(provider_type)) > 0

                        if type_match:
                            candidate_connections.append({
                                'member_id': member_id,
                                'provider_id': provider['ProviderID'],
                                'distance': float(provider['distance_km']),
                                'cost': provider.get('Cost', np.nan),
                                'rating': provider.get('CMS Rating', np.nan),
                                'member_source_type': member_source_type,
                                'provider_type': provider_type
                            })

            return candidate_connections

        except Exception as e:
            logger.error(f"Error finding candidate connections: {str(e)}")
            return []

    def optimize_assignments(self, candidate_connections, members_df, providers_df):
        """Optimize assignments per member and adjust until profit/loss ∈ [8%, 12%]."""
        assignments = []
        member_candidates = defaultdict(list)

        try:
            for connection in candidate_connections:
                member_candidates[connection['member_id']].append(connection)

            for _, member in members_df.iterrows():
                member_id = member['MemberID']
                assignment = {
                    'member_id': member_id,
                    'member_source_type': member['SourceType'],
                    'provider_id': None,
                    'distance': None,
                    'cost': None,
                    'rating': None,
                    'provider_type': None
                }

                if member_id in member_candidates:
                    best_provider = self.find_best_provider(member_candidates[member_id])
                    if best_provider:
                        assignment.update({
                            'provider_id': best_provider['provider_id'],
                            'distance': best_provider['distance'],
                            'cost': best_provider['cost'],
                            'rating': best_provider['rating'],
                            'provider_type': best_provider.get('provider_type')
                        })

                assignments.append(assignment)

            # ===============================
            # Adjustment loop for 8–12% band
            # ===============================
            original_cost = members_df['cost'].sum()
            min_bound, max_bound = self.cost_reduction_bounds

            def current_percentage():
                optimized_cost = sum(a['cost'] for a in assignments if a['cost'] is not None)
                return ((original_cost - optimized_cost) / original_cost) * 100 if original_cost > 0 else 0

            profit_loss_percentage = current_percentage()

            max_iterations = 50
            iteration = 0
            while (profit_loss_percentage < min_bound or profit_loss_percentage > max_bound) and iteration < max_iterations:
                iteration += 1

                if profit_loss_percentage < min_bound:
                    # Too low savings → pick cheaper alternatives
                    for a in assignments:
                        candidates = member_candidates.get(a['member_id'], [])
                        if not candidates:
                            continue
                        cheaper = [c for c in candidates if c['cost'] < (a['cost'] or float('inf'))]
                        if cheaper:
                            best_cheaper = min(cheaper, key=lambda c: c['cost'])
                            a.update(best_cheaper)

                elif profit_loss_percentage > max_bound:
                    # Too high savings → improve quality by choosing slightly costlier but better rated
                    for a in assignments:
                        candidates = member_candidates.get(a['member_id'], [])
                        if not candidates:
                            continue
                        higher_quality = [c for c in candidates if c['cost'] > (a['cost'] or 0) and c['rating'] > (a['rating'] or 0)]
                        if higher_quality:
                            best_quality = max(higher_quality, key=lambda c: (c['rating'], -c['cost']))
                            a.update(best_quality)

                profit_loss_percentage = current_percentage()

            logger.info(f"Final profit/loss after adjustment: {profit_loss_percentage:.2f}% (target {min_bound}-{max_bound}%)")
            return assignments

        except Exception as e:
            logger.error(f"Error in optimization assignments: {str(e)}")
            return []

    def analyze_by_source_type(self, assignments, members_df):
        """Analyze optimization results by member source type."""
        try:
            analysis = {}
            source_type_groups = defaultdict(list)
            for assignment in assignments:
                source_type = assignment['member_source_type']
                source_type_groups[source_type].append(assignment)

            for source_type, group_assignments in source_type_groups.items():
                total_members = len(group_assignments)
                served_members = len([a for a in group_assignments if a['provider_id'] is not None])

                analysis[source_type] = {
                    'total_members': total_members,
                    'served_members': served_members,
                    'unserved_members': total_members - served_members,
                    'access_percentage': (served_members / total_members) * 100 if total_members > 0 else 0,
                    'average_distance': np.mean([a['distance'] for a in group_assignments if a['distance'] is not None]) if any(a['distance'] is not None for a in group_assignments) else None,
                    'average_cost': np.mean([a['cost'] for a in group_assignments if a['cost'] is not None]) if any(a['cost'] is not None for a in group_assignments) else None,
                    'average_rating': np.mean([a['rating'] for a in group_assignments if a['rating'] is not None]) if any(a['rating'] is not None for a in group_assignments) else None
                }

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing by source type: {str(e)}")
            return {}

    def calculate_optimization_metrics(self, assignments, members_df, providers_df):
        """Calculate metrics including cost reduction constraint."""
        try:
            metrics = {}

            total_members = len(members_df)
            served_members = len([a for a in assignments if a['provider_id'] is not None])
            unserved_members = total_members - served_members
            access_percentage = (served_members / total_members) * 100 if total_members > 0 else 0

            original_total_cost = members_df['cost'].sum() if 'cost' in members_df.columns else 0
            optimized_total_cost = sum(a['cost'] for a in assignments if a['cost'] is not None and not pd.isna(a['cost']))
            cost_savings = original_total_cost - optimized_total_cost
            cost_savings_percentage = (cost_savings / original_total_cost) * 100 if original_total_cost > 0 else 0

            # check against constraint (8–12%)
            min_bound, max_bound = self.cost_reduction_bounds
            cost_constraint_satisfied = (min_bound <= cost_savings_percentage <= max_bound)

            used_provider_ids = set(a['provider_id'] for a in assignments if a['provider_id'] is not None)
            total_providers = len(providers_df)
            used_providers = len(used_provider_ids)
            provider_utilization = (used_providers / total_providers) * 100 if total_providers > 0 else 0

            served_assignments = [a for a in assignments if a['provider_id'] is not None]
            if served_assignments:
                average_distance = np.mean([a['distance'] for a in served_assignments])
                average_rating = np.mean([a['rating'] for a in served_assignments])
                max_distance = max([a['distance'] for a in served_assignments])
                min_distance = min([a['distance'] for a in served_assignments])
            else:
                average_distance = average_rating = max_distance = min_distance = 0

            if access_percentage == 100:
                network_status = "No need to change organization"
                network_recommendation = "Current network provides complete coverage"
            elif access_percentage >= 95:
                network_status = "Good in provider and member access"
                network_recommendation = "Network is performing well with minor optimization opportunities"
            else:
                network_status = "Organization must increase providers"
                network_recommendation = f"Network needs expansion - {unserved_members} members lack access"

            metrics = {
                'access': {
                    'total_members': total_members,
                    'served_members': served_members,
                    'unserved_members': unserved_members,
                    'access_percentage': access_percentage
                },
                'cost': {
                    'original_total_cost': original_total_cost,
                    'optimized_total_cost': optimized_total_cost,
                    'cost_savings': cost_savings,
                    'cost_savings_percentage': cost_savings_percentage,
                    'within_target_range': cost_constraint_satisfied,
                    'target_range': f"{min_bound}–{max_bound}%"
                },
                'provider_utilization': {
                    'total_providers': total_providers,
                    'used_providers': used_providers,
                    'unused_providers': total_providers - used_providers,
                    'utilization_percentage': provider_utilization
                },
                'quality_metrics': {
                    'average_distance_km': average_distance,
                    'average_provider_rating': average_rating,
                    'max_distance_km': max_distance,
                    'min_distance_km': min_distance
                },
                'network_assessment': {
                    'status': network_status,
                    'recommendation': network_recommendation
                }
            }

            return metrics

        except Exception as e:
            logger.error(f"Error calculating optimization metrics: {str(e)}")
            return {}

    def generate_optimization_report(self, assignments, members_df, providers_df):
        """Generate text report including cost reduction target."""
        try:
            metrics = self.calculate_optimization_metrics(assignments, members_df, providers_df)
            source_type_analysis = self.analyze_by_source_type(assignments, members_df)

            report_lines = []
            report_lines.append("=" * 80)
            report_lines.append("PROVIDER NETWORK OPTIMIZATION REPORT")
            report_lines.append("=" * 80)
            report_lines.append("")

            access = metrics.get('access', {})
            report_lines.append("ACCESS SUMMARY:")
            report_lines.append(f"  Total Members: {access.get('total_members', 0):,}")
            report_lines.append(f"  Served Members: {access.get('served_members', 0):,}")
            report_lines.append(f"  Unserved Members: {access.get('unserved_members', 0):,}")
            report_lines.append(f"  Access Percentage: {access.get('access_percentage', 0):.2f}%")
            report_lines.append("")

            cost = metrics.get('cost', {})
            report_lines.append("COST ANALYSIS:")
            report_lines.append(f"  Original Total Cost: ${cost.get('original_total_cost', 0):,.2f}")
            report_lines.append(f"  Optimized Total Cost: ${cost.get('optimized_total_cost', 0):,.2f}")
            report_lines.append(f"  Cost Savings: ${cost.get('cost_savings', 0):,.2f}")
            report_lines.append(f"  Savings Percentage: {cost.get('cost_savings_percentage', 0):.2f}%")
            report_lines.append(f"  Target Range: {cost.get('target_range', 'N/A')}")
            report_lines.append(f"  Within Target Range: {'✅ Yes' if cost.get('within_target_range') else '⚠️ No'}")
            report_lines.append("")

            provider_util = metrics.get('provider_utilization', {})
            report_lines.append("PROVIDER UTILIZATION:")
            report_lines.append(f"  Total Providers: {provider_util.get('total_providers', 0):,}")
            report_lines.append(f"  Used Providers: {provider_util.get('used_providers', 0):,}")
            report_lines.append(f"  Unused Providers: {provider_util.get('unused_providers', 0):,}")
            report_lines.append(f"  Utilization Rate: {provider_util.get('utilization_percentage', 0):.2f}%")
            report_lines.append("")

            quality = metrics.get('quality_metrics', {})
            report_lines.append("QUALITY METRICS:")
            report_lines.append(f"  Average Distance: {quality.get('average_distance_km', 0):.2f} km")
            report_lines.append(f"  Average Provider Rating: {quality.get('average_provider_rating', 0):.2f}/5")
            report_lines.append(f"  Distance Range: {quality.get('min_distance_km', 0):.2f} - {quality.get('max_distance_km', 0):.2f} km")
            report_lines.append("")

            if source_type_analysis:
                report_lines.append("ANALYSIS BY SOURCE TYPE:")
                for source_type, analysis in source_type_analysis.items():
                    report_lines.append(f"  {source_type}:")
                    report_lines.append(f"    Members: {analysis['served_members']}/{analysis['total_members']} served ({analysis['access_percentage']:.1f}%)")
                    if analysis['average_distance'] is not None and not np.isnan(analysis['average_distance']):
                        report_lines.append(f"    Avg Distance: {analysis['average_distance']:.2f} km")
                    if analysis['average_rating'] is not None and not np.isnan(analysis['average_rating']):
                        report_lines.append(f"    Avg Rating: {analysis['average_rating']:.2f}/5")
                report_lines.append("")

            assessment = metrics.get('network_assessment', {})
            report_lines.append("NETWORK ASSESSMENT:")
            report_lines.append(f"  Status: {assessment.get('status', 'Unknown')}")
            report_lines.append(f"  Recommendation: {assessment.get('recommendation', 'No recommendation available')}")
            report_lines.append("")

            report_lines.append("=" * 80)
            return "\n".join(report_lines)

        except Exception as e:
            logger.error(f"Error generating optimization report: {str(e)}")
            return f"Error generating report:{str(e)}"
