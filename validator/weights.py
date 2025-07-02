"""
Weights calculation and scoring logic for validators.
"""
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np
import structlog

from shared.types import Statement, MinerResponse, Resolution, ValidationResult


logger = structlog.get_logger()


class WeightsCalculator:
    """
    Calculates miner weights based on response accuracy and quality.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize weights calculator.
        
        Config options:
            - accuracy_weight: Weight for accuracy in scoring (0-1)
            - confidence_weight: Weight for confidence in scoring (0-1)
            - consistency_weight: Weight for consistency with consensus (0-1)
            - source_quality_weight: Weight for source quality (0-1)
        """
        config = config or {}
        self.accuracy_weight = config.get("accuracy_weight", 0.4)
        self.confidence_weight = config.get("confidence_weight", 0.2)
        self.consistency_weight = config.get("consistency_weight", 0.3)
        self.source_quality_weight = config.get("source_quality_weight", 0.1)
        
        # Normalize weights
        total_weight = (self.accuracy_weight + self.confidence_weight + 
                       self.consistency_weight + self.source_quality_weight)
        if total_weight > 0:
            self.accuracy_weight /= total_weight
            self.confidence_weight /= total_weight
            self.consistency_weight /= total_weight
            self.source_quality_weight /= total_weight
        
        # Track accumulated miner scores for weight setting
        self.accumulated_scores = defaultdict(list)
    
    def calculate_scores(
        self,
        statement: Statement,
        responses: List[MinerResponse],
        ground_truth: Optional[Resolution] = None,
        metagraph=None
    ) -> Dict[int, float]:
        """
        Calculate scores for each miner based on their responses.
        
        Args:
            statement: The statement being evaluated
            responses: List of miner responses
            ground_truth: Known correct answer (if available)
            metagraph: Bittensor metagraph for coldkey information
            
        Returns:
            Dictionary mapping miner UID to score (0-1)
        """
        if not responses:
            return {}
        
        # Calculate consensus if ground truth not available
        consensus = ground_truth or self._calculate_consensus(responses, metagraph)
        
        # Calculate individual scores
        scores = {}
        for response in responses:
            if response.miner_uid is not None:
                score = self._score_response(response, consensus, responses)
                scores[response.miner_uid] = score
        
        # Normalize scores
        scores = self._normalize_scores(scores)
        
        logger.info("Calculated miner scores",
                   num_miners=len(scores),
                   consensus=consensus.value if consensus else None)
        
        return scores
    
    def _calculate_consensus(self, responses: List[MinerResponse], metagraph=None) -> Optional[Resolution]:
        """
        Calculate consensus resolution from miner responses.
        
        Triple-layer Sybil protection system:
        1. Primary: Coldkey caps (7% per coldkey) + cross-coldkey similarity detection
        2. Fallback: Stake-based protection if coldkey lookup fails
        3. Final: Basic consensus if all protection fails
        """
        if not responses:
            return None
        
        # Try primary protection: coldkey-based with similarity detection
        if metagraph is not None:
            try:
                # Apply coldkey caps
                responses = self._apply_coldkey_consensus_cap(responses, metagraph)
                # Critical: Detect coordination ACROSS coldkeys
                responses = self._detect_cross_coldkey_similarity(responses, metagraph)
                logger.info("Using coldkey protection + cross-coldkey detection")
                return self._calculate_weighted_consensus(responses)
            except Exception as e:
                logger.warning(f"Coldkey protection failed: {e}, using stake fallback")
                try:
                    # Fallback: Stake-based protection
                    responses = self._apply_stake_based_protection(responses, metagraph)
                    logger.info("Using stake-based fallback protection")
                    return self._calculate_weighted_consensus(responses)
                except Exception as e2:
                    logger.error(f"Stake fallback failed: {e2}, using basic consensus")
        
        # Final fallback: basic consensus (no protection)
        logger.warning("No protection available, using basic consensus")
        return self._calculate_weighted_consensus(responses)
    
    def _calculate_weighted_consensus(self, responses: List[MinerResponse]) -> Optional[Resolution]:
        """Calculate final consensus from filtered responses."""
        # Count votes weighted by confidence
        vote_weights = defaultdict(float)
        
        for response in responses:
            weight = response.confidence / 100.0
            vote_weights[response.resolution] += weight
        
        # Find resolution with highest weight
        if vote_weights:
            consensus = max(vote_weights.items(), key=lambda x: x[1])[0]
            return consensus
        
        return None
    
    def _detect_cross_coldkey_similarity(self, responses: List[MinerResponse], metagraph) -> List[MinerResponse]:
        """
        Detect and limit responses from coldkeys controlling many miners.
        Applies rate limiting to prevent consensus manipulation.
        """
        if not hasattr(metagraph, 'coldkeys'):
            return responses
        
        # Group responses by coldkey
        coldkey_groups = defaultdict(list)
        for response in responses:
            try:
                coldkey = str(metagraph.coldkeys[response.miner_uid])
                coldkey_groups[coldkey].append(response)
            except (IndexError, KeyError):
                coldkey_groups["unknown"].append(response)
        
        # Target suspicious coldkeys with many miners
        filtered_responses = []
        suspicious_detected = False
        
        for coldkey, coldkey_responses in coldkey_groups.items():
            miner_count = len(coldkey_responses)
            
            # Suspicious pattern: Coldkey with excessive miners
            if miner_count >= 15:
                suspicious_detected = True
                logger.warning(f"SUSPICIOUS COLDKEY: {coldkey[:8]}... controls {miner_count} miners")
                
                # Severe limitation: Keep only 20% of responses
                max_allowed = max(2, int(miner_count * 0.20))
                
                import random
                limited_responses = random.sample(coldkey_responses, max_allowed)
                filtered_responses.extend(limited_responses)
                
                logger.info(f"Limited suspicious coldkey from {miner_count} to {max_allowed} responses")
            else:
                # Normal coldkey (<15 miners): Keep all responses
                filtered_responses.extend(coldkey_responses)
        
        if suspicious_detected:
            logger.warning(f"Suspicious coldkey detection: {len(responses)} → {len(filtered_responses)} responses")
        
        return filtered_responses
    
    def _apply_stake_based_protection(self, responses: List[MinerResponse], metagraph) -> List[MinerResponse]:
        """
        Stake-based fallback protection when coldkey method fails.
        Analyzes stake patterns to detect coordinated attacks.
        """
        if not hasattr(metagraph, 'S'):
            logger.warning("No stake data available")
            return responses
        
        # Analyze stake patterns to detect coordinated attacks
        stake_analysis = defaultdict(list)
        
        for response in responses:
            try:
                stake = float(metagraph.S[response.miner_uid])
                # Group by stake ranges to detect patterns
                stake_bucket = int(stake)  # Round to nearest TAO
                stake_analysis[stake_bucket].append(response)
            except (IndexError, KeyError, ValueError):
                stake_analysis[0].append(response)  # Unknown stake
        
        # Detect coordinated medium-stake attacks (the actual attack pattern)
        filtered_responses = []
        
        for stake_bucket, bucket_responses in stake_analysis.items():
            # Suspicious pattern: Many miners with similar stake amounts
            if 15 <= stake_bucket <= 100 and len(bucket_responses) >= 15:
                # Detected coordinated group
                logger.warning(f"Suspicious stake pattern detected: {len(bucket_responses)} miners with {stake_bucket} TAO each")
                
                # Severe limitation: Keep only 15% of this suspicious group
                max_allowed = max(1, int(len(bucket_responses) * 0.15))
                import random
                limited = random.sample(bucket_responses, max_allowed)
                filtered_responses.extend(limited)
                logger.info(f"Limited suspicious stake group from {len(bucket_responses)} to {len(limited)}")
            else:
                # Normal stake pattern: keep all
                filtered_responses.extend(bucket_responses)
        
        return filtered_responses
    
    def _apply_coldkey_consensus_cap(self, responses: List[MinerResponse], metagraph) -> List[MinerResponse]:
        """
        Apply 7% per-coldkey consensus cap to prevent Sybil attacks.
        
        Groups responses by coldkey and limits each coldkey's influence to 7% of total miners.
        This prevents coordinated attacks where multiple miners from the same entity
        manipulate consensus.
        """
        if not responses or not metagraph:
            return responses
        
        # Calculate 7% cap based on total network size
        total_miners = len(metagraph.coldkeys) if hasattr(metagraph, 'coldkeys') else len(responses)
        max_miners_per_coldkey = max(1, int(total_miners * 0.07))  # 7% cap, minimum 1
        
        # Group responses by coldkey
        coldkey_responses = defaultdict(list)
        capped_responses = []
        
        for response in responses:
            if response.miner_uid is not None and response.miner_uid < len(metagraph.coldkeys):
                try:
                    coldkey = str(metagraph.coldkeys[response.miner_uid])
                    coldkey_responses[coldkey].append(response)
                except (IndexError, AttributeError):
                    # If we can't get coldkey, include response without cap
                    capped_responses.append(response)
            else:
                # If we can't identify miner, include without cap
                capped_responses.append(response)
        
        # Apply cap to each coldkey group and detect coordination
        for coldkey, group_responses in coldkey_responses.items():
            # Check for suspicious coordination within this coldkey group
            if len(group_responses) > 1:
                coordination_penalty = self._detect_response_coordination(group_responses, coldkey)
                if coordination_penalty > 0:
                    # Apply coordination penalty by reducing confidence
                    for response in group_responses:
                        response.confidence = max(25, response.confidence * (1 - coordination_penalty))
            
            if len(group_responses) <= max_miners_per_coldkey:
                # Under cap - include all responses
                capped_responses.extend(group_responses)
            else:
                # Over cap - select top responses by confidence (after penalty)
                group_responses.sort(key=lambda r: r.confidence, reverse=True)
                selected = group_responses[:max_miners_per_coldkey]
                capped_responses.extend(selected)
                
                # Log the cap enforcement
                logger.warning(
                    "Applied coldkey consensus cap",
                    coldkey=coldkey[:12] + "...",
                    original_count=len(group_responses),
                    capped_count=len(selected),
                    max_allowed=max_miners_per_coldkey
                )
        
        # Log overall impact
        if len(capped_responses) < len(responses):
            logger.info(
                "Coldkey consensus cap applied",
                original_responses=len(responses),
                capped_responses=len(capped_responses),
                cap_percentage=7,
                max_per_coldkey=max_miners_per_coldkey
            )
        
        return capped_responses
    
    def _detect_response_coordination(self, responses: List[MinerResponse], coldkey: str) -> float:
        """
        Detect coordinated responses from miners under the same coldkey.
        
        Returns coordination penalty (0.0 to 1.0):
        - 0.0 = No coordination detected
        - 1.0 = Maximum coordination (identical responses)
        """
        if len(responses) < 2:
            return 0.0
        
        # Check resolution agreement rate
        resolutions = [r.resolution for r in responses]
        resolution_agreement = len([r for r in resolutions if r == resolutions[0]]) / len(resolutions)
        
        # Check confidence similarity (suspicious if all very similar)
        confidences = [r.confidence for r in responses]
        conf_mean = sum(confidences) / len(confidences)
        conf_variance = sum((c - conf_mean) ** 2 for c in confidences) / len(confidences)
        conf_std = conf_variance ** 0.5
        
        # Check summary similarity (basic text comparison)
        summaries = [r.summary.lower() for r in responses]
        summary_similarity = self._calculate_text_similarity(summaries)
        
        # Calculate coordination score
        coordination_indicators = []
        
        # 1. Perfect resolution agreement is suspicious (weight: 0.4)
        if resolution_agreement >= 0.9:  # 90%+ agreement
            coordination_indicators.append(0.4 * resolution_agreement)
        
        # 2. Very low confidence variance is suspicious (weight: 0.3)
        if conf_std < 5.0:  # Standard deviation < 5%
            coordination_indicators.append(0.3 * (1 - conf_std / 5.0))
        
        # 3. High summary similarity is suspicious (weight: 0.3)
        if summary_similarity > 0.7:  # 70%+ text similarity
            coordination_indicators.append(0.3 * summary_similarity)
        
        # Combine indicators
        coordination_score = sum(coordination_indicators)
        
        # Log coordination detection
        if coordination_score > 0.3:  # 30% threshold for logging
            logger.warning(
                "Coordination detected",
                coldkey=coldkey[:12] + "...",
                miner_count=len(responses),
                resolution_agreement=f"{resolution_agreement:.2f}",
                confidence_std=f"{conf_std:.2f}",
                summary_similarity=f"{summary_similarity:.2f}",
                coordination_score=f"{coordination_score:.2f}"
            )
        
        return min(coordination_score, 1.0)  # Cap at 1.0
    
    def _calculate_text_similarity(self, texts: List[str]) -> float:
        """
        Calculate average similarity between all text pairs.
        Simple word-based similarity for detecting copy-paste responses.
        """
        if len(texts) < 2:
            return 0.0
        
        similarities = []
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = self._jaccard_similarity(texts[i], texts[j])
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts (word-based)."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _score_response(
        self,
        response: MinerResponse,
        consensus: Optional[Resolution],
        all_responses: List[MinerResponse]
    ) -> float:
        """
        Score an individual response.
        
        Components:
        1. Accuracy: How close to consensus/truth
        2. Confidence: Appropriate confidence level
        3. Consistency: Agreement with other high-quality responses
        4. Source Quality: Quality and diversity of sources
        """
        scores = []
        
        # 1. Accuracy score
        accuracy_score = self._calculate_accuracy_score(response, consensus)
        scores.append(accuracy_score * self.accuracy_weight)
        
        # 2. Confidence score
        confidence_score = self._calculate_confidence_score(response, consensus)
        scores.append(confidence_score * self.confidence_weight)
        
        # 3. Consistency score
        consistency_score = self._calculate_consistency_score(response, all_responses)
        scores.append(consistency_score * self.consistency_weight)
        
        # 4. Source quality score
        source_score = self._calculate_source_score(response)
        scores.append(source_score * self.source_quality_weight)
        
        # Combine scores
        total_score = sum(scores)
        
        return min(max(total_score, 0.0), 1.0)  # Clamp to [0, 1]
    
    def _calculate_accuracy_score(
        self,
        response: MinerResponse,
        consensus: Optional[Resolution]
    ) -> float:
        """Calculate accuracy score based on agreement with consensus."""
        if not consensus:
            return 0.5  # Neutral score if no consensus
        
        if response.resolution == consensus:
            return 1.0
        elif response.resolution == Resolution.PENDING:
            return 0.5  # Partial credit for being uncertain
        else:
            return 0.0
    
    def _calculate_confidence_score(
        self,
        response: MinerResponse,
        consensus: Optional[Resolution]
    ) -> float:
        """
        Calculate confidence score.
        
        Rewards appropriate confidence levels:
        - High confidence for clear resolutions
        - Lower confidence for PENDING
        - Penalizes overconfidence on wrong answers
        """
        confidence = response.confidence / 100.0
        
        if response.resolution == consensus:
            # Correct answer - reward high confidence
            return confidence
        elif response.resolution == Resolution.PENDING:
            # Pending - moderate confidence is good
            target_confidence = 0.5
            distance = abs(confidence - target_confidence)
            return 1.0 - distance
        else:
            # Wrong answer - penalize high confidence
            return 1.0 - confidence
    
    def _calculate_consistency_score(
        self,
        response: MinerResponse,
        all_responses: List[MinerResponse]
    ) -> float:
        """
        Calculate consistency with other high-confidence responses.
        """
        if len(all_responses) < 2:
            return 1.0  # No comparison possible
        
        # Find high-confidence responses (>80%)
        high_conf_responses = [
            r for r in all_responses 
            if r.confidence > 80 and r != response
        ]
        
        if not high_conf_responses:
            return 1.0  # No high-confidence peers
        
        # Calculate agreement rate
        agreements = sum(
            1 for r in high_conf_responses 
            if r.resolution == response.resolution
        )
        
        return agreements / len(high_conf_responses)
    
    def _calculate_source_score(self, response: MinerResponse) -> float:
        """
        Calculate source quality score.
        
        Considers:
        - Number of sources
        - Source diversity
        - Known reliable sources
        """
        if not response.sources:
            return 0.0
        
        # Reliable source patterns
        reliable_sources = [
            "coingecko", "coinmarketcap", "yahoo", "bloomberg",
            "reuters", "binance", "coinbase", "kraken"
        ]
        
        # Count sources
        num_sources = len(response.sources)
        source_count_score = min(num_sources / 3.0, 1.0)  # Max benefit at 3 sources
        
        # Check for reliable sources
        reliable_count = sum(
            1 for source in response.sources
            if any(reliable in source.lower() for reliable in reliable_sources)
        )
        reliability_score = min(reliable_count / 2.0, 1.0)  # Max at 2 reliable
        
        # Combine scores
        return (source_count_score + reliability_score) / 2.0
    
    def _normalize_scores(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        Normalize scores to sum to 1.0 for weight setting.
        """
        if not scores:
            return {}
        
        total = sum(scores.values())
        if total == 0:
            # Equal weights if all scores are 0
            equal_weight = 1.0 / len(scores)
            return {uid: equal_weight for uid in scores}
        
        # Normalize
        return {uid: score / total for uid, score in scores.items()}
    
    def calculate_consensus(
        self,
        statement: Statement,
        responses: List[MinerResponse],
        metagraph=None
    ) -> ValidationResult:
        """
        Calculate consensus result from miner responses.
        
        Args:
            statement: Statement being evaluated
            responses: List of miner responses
            metagraph: Bittensor metagraph for coldkey-based Sybil protection
        
        Returns:
            ValidationResult with consensus information
        """
        if not responses:
            return ValidationResult(
                consensus_resolution=Resolution.PENDING,
                consensus_confidence=0.0,
                total_responses=0,
                valid_responses=0
            )
        
        # Filter valid responses
        valid_responses = [r for r in responses if r.is_valid()]
        
        # Calculate consensus with coldkey protection
        consensus = self._calculate_consensus(valid_responses, metagraph)
        
        # Calculate average confidence for consensus resolution
        consensus_responses = [
            r for r in valid_responses 
            if r.resolution == consensus
        ]
        
        avg_confidence = 0.0
        if consensus_responses:
            avg_confidence = sum(r.confidence for r in consensus_responses) / len(consensus_responses)
        
        # Calculate miner scores with metagraph
        scores = self.calculate_scores(statement, valid_responses, metagraph=metagraph)
        
        # Collect unique sources
        all_sources = set()
        for response in valid_responses:
            all_sources.update(response.sources)
        
        # Store scores for weight calculation
        for miner_uid, score in scores.items():
            self.accumulated_scores[miner_uid].append(score)
            # Keep only recent scores (last 100)
            if len(self.accumulated_scores[miner_uid]) > 100:
                self.accumulated_scores[miner_uid] = self.accumulated_scores[miner_uid][-100:]
        
        return ValidationResult(
            consensus_resolution=consensus or Resolution.PENDING,
            consensus_confidence=avg_confidence,
            total_responses=len(responses),
            valid_responses=len(valid_responses),
            miner_scores=scores,
            consensus_sources=list(all_sources)[:10]  # Top 10 sources
        )
    
    def get_miner_scores(self) -> Dict[int, float]:
        """
        Get accumulated miner scores for weight setting.
        
        Returns:
            Dictionary mapping miner UID to average score
        """
        if not self.accumulated_scores:
            return {}
        
        # Calculate average scores
        avg_scores = {}
        for miner_uid, scores in self.accumulated_scores.items():
            if scores:
                avg_scores[miner_uid] = sum(scores) / len(scores)
        
        # Normalize scores for weight setting
        return self._normalize_scores(avg_scores)