"""
Market Researcher Agent - Real-time Financial Intelligence
=========================================================

This agent researches current market rates, competitor offerings, and trends
to provide up-to-date information for loan recommendations.
"""

import logging
import asyncio
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from .base import BaseAgent

logger = logging.getLogger(__name__)


class MarketRate(BaseModel):
    """Market rate information for a specific loan product"""
    lender_name: str
    loan_type: str
    min_rate: float
    max_rate: float
    processing_fee: str
    min_amount: int
    max_amount: int
    last_updated: datetime
    source: str


class MarketAnalysis(BaseModel):
    """Comprehensive market analysis results"""
    average_rate: float
    lowest_rate: float
    highest_rate: float
    rate_trend: str  # "rising", "falling", "stable"
    competitive_position: str
    market_insights: List[str]
    data_freshness: str


class MarketResearcherAgent(BaseAgent):
    """
    Agent that researches real-time market data, competitor rates,
    and financial trends to inform loan recommendations.
    """
    
    def __init__(self, openai_client, storage_service, graph_intelligence=None, conversation_memory=None):
        system_prompt = """You are a financial market research analyst specializing in lending markets.

Your capabilities include:
- **Real-time rate research** from multiple financial institutions
- **Competitive analysis** and market positioning
- **Trend identification** and pattern recognition
- **Data synthesis** from multiple sources
- **Market intelligence** for strategic decision making

Research Areas:
1. Current interest rates across different lenders
2. Processing fees and charges comparison
3. Loan product feature analysis
4. Market trends and rate movements
5. Regulatory changes affecting lending
6. Economic indicators impacting rates

Tools Available:
- Web scraping for real-time rates
- API integrations with financial data providers
- Trend analysis algorithms
- Competitive intelligence systems
- Economic data integration

Your Analysis Framework:
1. Gather data from multiple reliable sources
2. Validate and cross-reference information
3. Identify patterns and trends
4. Provide actionable market insights
5. Flag opportunities and risks

Always provide:
- Current, accurate market data
- Context for rate movements
- Competitive positioning advice
- Market timing recommendations
- Data source transparency"""

        super().__init__(
            name="Market Researcher Agent",
            description="Financial market intelligence and competitive analysis specialist",
            system_prompt=system_prompt,
            openai_client=openai_client,
            storage_service=storage_service,
            graph_intelligence=graph_intelligence,
            conversation_memory=conversation_memory
        )
        
        # Market data cache
        self.rate_cache = {}
        self.cache_expiry = timedelta(hours=4)  # Cache rates for 4 hours
        
    def _register_tools(self):
        """Register market research tools"""
        
        def fetch_current_rates(loan_type: str = "personal_loan") -> Dict[str, Any]:
            """Fetch current market rates for loans"""
            # Simulated market data - in production, would fetch from real APIs
            market_rates = {
                "personal_loan": {
                    "min_rate": 10.5,
                    "max_rate": 24.0,
                    "avg_rate": 15.5,
                    "top_lenders": [
                        {"name": "HDFC Bank", "rate": 10.5, "processing_fee": "2%"},
                        {"name": "ICICI Bank", "rate": 11.25, "processing_fee": "2.5%"},
                        {"name": "SBI", "rate": 11.50, "processing_fee": "1%"}
                    ]
                },
                "business_loan": {
                    "min_rate": 9.5,
                    "max_rate": 20.0,
                    "avg_rate": 13.5,
                    "top_lenders": [
                        {"name": "HDFC Bank", "rate": 9.5, "processing_fee": "1%"},
                        {"name": "ICICI Bank", "rate": 10.0, "processing_fee": "1.5%"},
                        {"name": "Axis Bank", "rate": 10.25, "processing_fee": "1%"}
                    ]
                }
            }
            
            return market_rates.get(loan_type, market_rates["personal_loan"])
        
        def analyze_rate_trends(period_months: int = 12) -> Dict[str, Any]:
            """Analyze interest rate trends over specified period"""
            return {
                "trend_direction": "stable",
                "rate_change_percentage": -0.25,
                "market_outlook": "Rates expected to remain stable",
                "best_time_to_apply": "Current rates are favorable",
                "historical_data": {
                    "6_months_ago": 15.75,
                    "3_months_ago": 15.50,
                    "current": 15.25
                }
            }
        
        def compare_lenders(loan_amount: float, loan_type: str = "personal_loan") -> Dict[str, Any]:
            """Compare different lenders for given loan requirements"""
            lenders = [
                {
                    "name": "HDFC Bank",
                    "interest_rate": 10.5,
                    "processing_fee_percent": 2.0,
                    "max_amount": 2000000,
                    "min_amount": 50000,
                    "tenure_options": [12, 24, 36, 48, 60],
                    "special_features": ["Pre-closure allowed", "Quick approval"],
                    "rating": 4.5
                },
                {
                    "name": "ICICI Bank", 
                    "interest_rate": 11.25,
                    "processing_fee_percent": 2.5,
                    "max_amount": 1500000,
                    "min_amount": 30000,
                    "tenure_options": [12, 24, 36, 48],
                    "special_features": ["Digital process", "Instant approval"],
                    "rating": 4.3
                },
                {
                    "name": "SBI",
                    "interest_rate": 11.50,
                    "processing_fee_percent": 1.0,
                    "max_amount": 2000000,
                    "min_amount": 25000,
                    "tenure_options": [12, 24, 36, 48, 60, 72],
                    "special_features": ["Low processing fee", "Government bank"],
                    "rating": 4.1
                }
            ]
            
            # Filter lenders based on loan amount
            suitable_lenders = [
                lender for lender in lenders 
                if lender["min_amount"] <= loan_amount <= lender["max_amount"]
            ]
            
            # Calculate total cost for each lender
            for lender in suitable_lenders:
                processing_fee = loan_amount * (lender["processing_fee_percent"] / 100)
                lender["processing_fee_amount"] = processing_fee
                
                # Calculate EMI for 36 months as standard comparison
                monthly_rate = lender["interest_rate"] / (12 * 100)
                tenure = 36
                emi = loan_amount * monthly_rate * (1 + monthly_rate)**tenure / ((1 + monthly_rate)**tenure - 1)
                total_payment = emi * tenure
                
                lender["emi_36_months"] = round(emi, 2)
                lender["total_cost"] = round(total_payment + processing_fee, 2)
            
            # Sort by total cost
            suitable_lenders.sort(key=lambda x: x["total_cost"])
            
            return {
                "suitable_lenders": suitable_lenders,
                "comparison_summary": self._create_lender_comparison(suitable_lenders),
                "recommendation": suitable_lenders[0] if suitable_lenders else None
            }
        
        def get_market_insights(user_profile: Dict[str, Any]) -> Dict[str, Any]:
            """Get personalized market insights based on user profile"""
            insights = {
                "market_position": "Favorable lending environment",
                "rate_competitiveness": "Current rates are competitive",
                "timing_recommendation": "Good time to apply for loans",
                "market_trends": [
                    "Digital lending processes becoming faster",
                    "Increased competition leading to better rates",
                    "Focus on customer experience improvements"
                ],
                "personalized_tips": self._get_personalized_market_tips(user_profile)
            }
            
            return insights
        
        def analyze_loan_deals(loan_requirements: Dict[str, Any]) -> Dict[str, Any]:
            """Analyze current loan deals and offers"""
            current_deals = [
                {
                    "lender": "HDFC Bank",
                    "offer": "0.5% rate reduction for salary account holders",
                    "validity": "Limited time offer",
                    "conditions": ["Salary account required", "Minimum income 50k"]
                },
                {
                    "lender": "ICICI Bank",
                    "offer": "No processing fee for online applications",
                    "validity": "This month only",
                    "conditions": ["Online application", "Quick approval process"]
                }
            ]
            
            return {
                "current_deals": current_deals,
                "deal_analysis": self._analyze_deal_value(current_deals, loan_requirements),
                "recommendations": self._recommend_best_deals(current_deals, loan_requirements)
            }
        
        def generate_market_report(user_context: Dict[str, Any]) -> Dict[str, Any]:
            """Generate comprehensive market report"""
            return {
                "executive_summary": "Personal loan market remains competitive with stable rates",
                "key_findings": [
                    "Interest rates have stabilized around 15.5% average",
                    "Processing fees range from 1-2.5%",
                    "Digital processes becoming standard"
                ],
                "recommendations": [
                    "Compare multiple lenders before deciding",
                    "Consider total cost, not just interest rate",
                    "Look for pre-closure flexibility"
                ],
                "market_outlook": "Stable rates expected for next 6 months"
            }
        
        # Store tool functions as instance methods
        self.fetch_current_rates = fetch_current_rates
        self.analyze_rate_trends = analyze_rate_trends
        self.compare_lenders = compare_lenders
        self.get_market_insights = get_market_insights
        self.analyze_loan_deals = analyze_loan_deals
        self.generate_market_report = generate_market_report
    
    def _simulate_market_rates(self, loan_type: str) -> List[MarketRate]:
        """Simulate current market rates (replace with real API calls in production)"""
        base_rates = {
            "personal_loan": 12.99,
            "business_loan": 15.99,
            "education_loan": 9.99
        }
        
        lenders = [
            "HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Bank",
            "Bajaj Finserv", "Tata Capital", "Fullerton India", "IndusInd Bank"
        ]
        
        base_rate = base_rates.get(loan_type, 15.99)
        market_rates = []
        
        for i, lender in enumerate(lenders):
            # Add some variation to rates
            variation = (i - 4) * 0.5  # -2% to +2% variation
            min_rate = max(8.99, base_rate + variation)
            max_rate = min_rate + 3.0 + (i * 0.2)
            
            rate = MarketRate(
                lender_name=lender,
                loan_type=loan_type,
                min_rate=round(min_rate, 2),
                max_rate=round(max_rate, 2),
                processing_fee=f"Up to {2 + (i % 3)}% of loan amount",
                min_amount=25000 if loan_type == "personal_loan" else 100000,
                max_amount=1000000 if loan_type == "personal_loan" else 5000000,
                last_updated=datetime.now(),
                source="Simulated Data"
            )
            market_rates.append(rate)
        
        return market_rates
    
    def _simulate_rate_trends(self, loan_type: str, days: int) -> Dict[str, Any]:
        """Simulate rate trend analysis"""
        import random
        
        trend_directions = ["rising", "falling", "stable"]
        direction = random.choice(trend_directions)
        
        change_pct = 0
        if direction == "rising":
            change_pct = random.uniform(0.1, 0.8)
        elif direction == "falling":
            change_pct = random.uniform(-0.8, -0.1)
        else:
            change_pct = random.uniform(-0.2, 0.2)
        
        factors = {
            "rising": ["RBI repo rate increase", "Inflation concerns", "Credit demand surge"],
            "falling": ["RBI rate cuts", "Increased competition", "Economic slowdown"],
            "stable": ["Stable monetary policy", "Balanced market conditions", "Steady demand"]
        }
        
        return {
            "direction": direction,
            "change_pct": round(change_pct, 2),
            "factors": factors[direction],
            "forecast": f"Rates expected to {direction.replace('stable', 'remain stable')} in next 30 days",
            "confidence": random.uniform(0.7, 0.9)
        }
    
    def _estimate_lendenclub_rate(self, loan_type: str, user_profile: Dict[str, Any]) -> float:
        """Estimate LendenClub's rate for comparison"""
        base_rates = {
            "personal_loan": 14.99,
            "business_loan": 17.99,
            "education_loan": 11.99
        }
        
        base_rate = base_rates.get(loan_type, 16.99)
        
        # Adjust based on user profile
        if user_profile.get("credit_score", 650) >= 750:
            base_rate -= 2.0
        elif user_profile.get("credit_score", 650) >= 700:
            base_rate -= 1.0
        
        return round(base_rate, 2)
    
    def _calculate_percentile(self, rate: float, market_rates: List[float]) -> int:
        """Calculate what percentile our rate is in the market"""
        if not market_rates:
            return 50
        
        sorted_rates = sorted(market_rates)
        position = 0
        for i, market_rate in enumerate(sorted_rates):
            if rate <= market_rate:
                position = i
                break
        else:
            position = len(sorted_rates)
        
        percentile = (position / len(sorted_rates)) * 100
        return int(percentile)
    
    def _identify_advantages(self, loan_type: str) -> List[str]:
        """Identify LendenClub's competitive advantages"""
        return [
            "P2P lending model offers competitive rates",
            "Fast digital approval process",
            "Transparent fee structure",
            "Flexible repayment options",
            "Strong customer support"
        ]
    
    def _identify_opportunities(self, market_rates: List[MarketRate], loan_type: str) -> List[str]:
        """Identify market opportunities"""
        avg_rate = sum(rate.min_rate for rate in market_rates) / len(market_rates)
        
        opportunities = []
        if avg_rate > 16:
            opportunities.append("High market rates create opportunity for competitive positioning")
        
        opportunities.extend([
            "Growing demand for digital lending solutions",
            "Increasing awareness of P2P lending benefits",
            "Opportunity to capture underserved segments"
        ])
        
        return opportunities
    
    def _generate_competitive_recommendations(self, our_rate: float, market_rates: List[float]) -> List[str]:
        """Generate competitive recommendations"""
        if not market_rates:
            return ["Insufficient market data for recommendations"]
        
        avg_market = sum(market_rates) / len(market_rates)
        min_market = min(market_rates)
        
        recommendations = []
        
        if our_rate > avg_market:
            recommendations.append("Consider rate adjustments to match market average")
        elif our_rate < min_market:
            recommendations.append("Excellent competitive position - leverage in marketing")
        
        recommendations.extend([
            "Emphasize unique P2P lending advantages",
            "Focus on digital experience differentiation",
            "Highlight transparent fee structure"
        ])
        
        return recommendations
    
    def _calculate_deal_score(self, rate: MarketRate, amount: float, user_profile: Dict[str, Any]) -> float:
        """Calculate a comprehensive score for a loan deal"""
        score = 100
        
        # Rate component (40% weight)
        if rate.min_rate <= 12:
            score += 40
        elif rate.min_rate <= 15:
            score += 30
        elif rate.min_rate <= 18:
            score += 20
        else:
            score += 10
        
        # Amount eligibility (20% weight)
        if amount <= rate.max_amount:
            score += 20
        else:
            score += 10
        
        # Lender reputation (20% weight)
        reputation_scores = {
            "HDFC Bank": 18, "ICICI Bank": 17, "SBI": 16, "Axis Bank": 15,
            "Kotak Bank": 14, "LendenClub": 19  # P2P advantage
        }
        score += reputation_scores.get(rate.lender_name, 12)
        
        # Processing fee (20% weight)
        if "1%" in rate.processing_fee:
            score += 20
        elif "2%" in rate.processing_fee:
            score += 15
        elif "3%" in rate.processing_fee:
            score += 10
        else:
            score += 5
        
        return round(score, 1)
    
    def _get_lender_pros(self, lender_name: str) -> List[str]:
        """Get pros for specific lenders"""
        lender_pros = {
            "HDFC Bank": ["Strong brand reputation", "Wide branch network", "Good customer service"],
            "ICICI Bank": ["Digital-first approach", "Quick approvals", "Competitive rates"],
            "SBI": ["Lowest processing fees", "Government backing", "Extensive reach"],
            "LendenClub": ["P2P model benefits", "Transparent pricing", "Quick digital process"]
        }
        return lender_pros.get(lender_name, ["Established lender", "Multiple products"])
    
    def _get_lender_cons(self, lender_name: str) -> List[str]:
        """Get cons for specific lenders"""
        lender_cons = {
            "HDFC Bank": ["Higher processing fees", "Strict eligibility"],
            "ICICI Bank": ["Variable rate fluctuations", "Hidden charges"],
            "SBI": ["Slow processing", "Bureaucratic procedures"],
            "LendenClub": ["Newer platform", "P2P risks"]
        }
        return lender_cons.get(lender_name, ["Standard lending terms"])
    
    def _get_suitability(self, lender_name: str, user_profile: Dict[str, Any]) -> str:
        """Determine suitability for user profile"""
        credit_score = user_profile.get("credit_score", 650)
        income = user_profile.get("monthly_income", 50000)
        
        if credit_score >= 750 and income >= 100000:
            return "Excellent profile - all lenders suitable"
        elif credit_score >= 700:
            return "Good profile - most lenders suitable"
        else:
            return "Consider improving credit score for better options"
    
    def _assess_market_sentiment(self) -> str:
        """Assess overall market sentiment"""
        return "Cautiously optimistic with stable lending conditions"
    
    def _analyze_rbi_policy(self) -> str:
        """Analyze RBI policy impact"""
        return "Current repo rate at 6.5% supporting moderate lending rates"
    
    def _get_economic_indicators(self) -> Dict[str, str]:
        """Get relevant economic indicators"""
        return {
            "inflation": "5.8% - within RBI target range",
            "gdp_growth": "6.2% - supporting credit demand",
            "employment": "Stable - supporting loan repayment capacity"
        }
    
    def _assess_lending_environment(self) -> str:
        """Assess overall lending environment"""
        return "Favorable for borrowers with increased competition among lenders"
    
    def _recommend_timing(self) -> str:
        """Recommend optimal timing for loan applications"""
        return "Good time to apply - rates stable with competitive market"
    
    def _identify_market_risks(self) -> List[str]:
        """Identify current market risks"""
        return [
            "Potential RBI rate hikes if inflation rises",
            "Economic uncertainty affecting lending standards",
            "Regulatory changes in P2P lending space"
        ]
    
    def _compare_prepayment_policies(self, loan_type: str) -> Dict[str, str]:
        """Compare prepayment policies across lenders"""
        return {
            "HDFC Bank": "2% after 12 months",
            "ICICI Bank": "4% anytime",
            "SBI": "No charges after 6 months",
            "LendenClub": "1% after 6 months"
        }
    
    def _compare_processing_fees(self, loan_type: str) -> Dict[str, str]:
        """Compare processing fees"""
        return {
            "HDFC Bank": "Up to 2.5%",
            "ICICI Bank": "Up to 3%",
            "SBI": "0.35% to 1%",
            "LendenClub": "Up to 2%"
        }
    
    def _compare_documentation_requirements(self, loan_type: str) -> Dict[str, str]:
        """Compare documentation requirements"""
        return {
            "Traditional Banks": "Extensive paperwork, multiple visits",
            "Private Banks": "Moderate documentation, some digital",
            "LendenClub": "Minimal paperwork, fully digital process"
        }
    
    def _compare_approval_times(self, loan_type: str) -> Dict[str, str]:
        """Compare approval times"""
        return {
            "HDFC Bank": "3-7 days",
            "ICICI Bank": "2-5 days",
            "SBI": "7-14 days",
            "LendenClub": "24-48 hours"
        }
    
    def _compare_customer_service(self, loan_type: str) -> Dict[str, str]:
        """Compare customer service quality"""
        return {
            "HDFC Bank": "Good branch + digital support",
            "ICICI Bank": "Strong digital support",
            "SBI": "Extensive branch network",
            "LendenClub": "Dedicated relationship managers"
        }
    
    def _compare_digital_features(self, loan_type: str) -> Dict[str, str]:
        """Compare digital features"""
        return {
            "Traditional Banks": "Basic mobile apps",
            "New-age Banks": "Advanced digital features",
            "LendenClub": "AI-powered platform with full digital journey"
        } 