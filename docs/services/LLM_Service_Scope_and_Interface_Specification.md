# LLM Service Scope and Interface Specification - Drupal Ticket Generator

## Overview
Clarification of LLM service responsibilities, interface definition, and implementation scope to resolve conflicting specifications about what the LLM service should actually do.

## Conflicting Specifications Identified

### **Conflict 1: Implementation Scope**
- **`missing_implementation_decisions.md`**: Shows minimal interface with just `explain_error()` placeholder
- **`claude_code_instructions.md`**: Says "Create LLMService interface (no implementation needed yet)"
- **Service architecture docs**: Reference LLMService for actual ticket generation

### **Conflict 2: Functionality Scope**
- **Error explanations only**: Some docs suggest LLM is just for explaining validation errors
- **Full ticket generation**: Processing service architecture assumes LLM generates ticket content
- **Provider abstraction**: Unclear whether multi-provider support is needed

### **Conflict 3: Integration Points**
- **ProcessingService**: References `llm_service` for ticket generation
- **UploadService**: References `llm_service` for error explanations
- **Unclear boundaries**: What each service expects from LLM service

## Decision: Comprehensive LLM Service with Phased Implementation

### **Full Interface Definition** (Complete contract)
```python
# /backend/app/integrations/llm/interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID

class LLMServiceInterface(ABC):
    """
    LLM service interface supporting both ticket generation and error explanation.
    Provides provider abstraction for OpenAI and Anthropic.
    """
    
    # Core Configuration
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name: 'openai' or 'anthropic'"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return model name: 'gpt-4o', 'claude-3-sonnet-20240229', etc."""
        pass
    
    # Health and Validation
    @abstractmethod
    async def validate_connectivity(self) -> Dict[str, any]:
        """
        Test LLM service connectivity and return health status.
        Returns: {
            "status": "healthy|degraded|unavailable",
            "connectivity": "ok|timeout|unreachable", 
            "authentication": "valid|invalid|expired",
            "quota_status": "available|low|exceeded",
            "model_availability": "available|unavailable|deprecated"
        }
        """
        pass
    
    @abstractmethod
    async def estimate_cost(self, total_entities: int, provider: str) -> Dict[str, any]:
        """
        Estimate processing cost for given entity count.
        Returns: {
            "estimated_cost": 1.85,
            "estimated_tokens": 12000,
            "quota_remaining": 500.0
        }
        """
        pass
    
    # Ticket Generation (Core functionality)
    @abstractmethod
    async def generate_ticket_content(self, entity_data: Dict, context: Dict) -> Dict[str, str]:
        """
        Generate ticket content from CSV entity data.
        
        Args:
            entity_data: Parsed CSV entity (bundle, field, view, etc.)
            context: {
                "entity_type": "bundle|field|view|etc",
                "csv_source": "bundles.csv",
                "related_entities": [...],  # Cross-references
                "site_context": "Project name and description"
            }
            
        Returns: {
            "title": "Configure Product Bundle",
            "user_story": "As a content manager, I need...",
            "analysis": "This bundle will...",
            "verification": "✅ Bundle created\n✅ Fields configured...",
            "estimated_hours": "2-4 hours"
        }
        """
        pass
    
    @abstractmethod
    async def generate_dependency_analysis(self, entities: List[Dict]) -> Dict[str, List[str]]:
        """
        Analyze entity dependencies for implementation ordering.
        
        Args:
            entities: List of entity data from all CSV files
            
        Returns: {
            "dependencies": {
                "entity_id_1": ["entity_id_2", "entity_id_3"],  # entity_1 depends on entity_2, entity_3
                "entity_id_4": []  # No dependencies
            },
            "entity_groups": {
                "Content": ["entity_id_1", "entity_id_2"],
                "Media": ["entity_id_3"]
            }
        }
        """
        pass
    
    # Error Explanation (Secondary functionality)
    @abstractmethod
    async def explain_error(self, error_context: Dict) -> str:
        """
        Generate user-friendly explanation of validation/processing errors.
        
        Args:
            error_context: {
                "error_type": "missing_reference|validation_failed|processing_error",
                "error_message": "Original technical error message",
                "context": "CSV file and row information",
                "user_data": "User's input that caused error"
            }
            
        Returns: User-friendly explanation with suggested actions
        """
        pass
```

### **Implementation Strategy: Two Phases**

#### **Phase 1: MVP Implementation (For Claude Code)**
```python
# /backend/app/integrations/llm/service.py
class LLMService(LLMServiceInterface):
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        # Initialize based on environment settings
        
    # FULL IMPLEMENTATION REQUIRED:
    async def validate_connectivity(self) -> Dict[str, any]:
        # Real connectivity check - prevents expensive processing failures
        
    async def estimate_cost(self, total_entities: int, provider: str) -> Dict[str, any]:
        # Real cost estimation - user transparency requirement
        
    async def generate_ticket_content(self, entity_data: Dict, context: Dict) -> Dict[str, str]:
        # CORE FUNCTIONALITY - Real LLM integration for ticket generation
        # This is the primary value proposition of the application
        
    # PLACEHOLDER IMPLEMENTATIONS:
    async def generate_dependency_analysis(self, entities: List[Dict]) -> Dict[str, List[str]]:
        # Placeholder: Use hardcoded Drupal relationship rules
        # Future: LLM-enhanced dependency detection
        
    async def explain_error(self, error_context: Dict) -> str:
        # Placeholder: Return formatted version of original error
        # Future: LLM-generated user-friendly explanations
```

#### **Phase 2: Enhanced Implementation (Future)**
- LLM-enhanced dependency analysis
- Sophisticated error explanations  
- Multi-provider load balancing
- Advanced prompt optimization

## Provider Implementation Structure

### **Provider Abstraction**
```python
# /backend/app/integrations/llm/providers/base.py
class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_completion(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def estimate_tokens(self, prompt: str) -> int:
        pass

# /backend/app/integrations/llm/providers/openai_provider.py
class OpenAIProvider(BaseLLMProvider):
    # Real OpenAI API integration
    
# /backend/app/integrations/llm/providers/anthropic_provider.py  
class AnthropicProvider(BaseLLMProvider):
    # Real Anthropic API integration
```

### **Service Implementation**
```python
# /backend/app/integrations/llm/service.py
class LLMService(LLMServiceInterface):
    def __init__(self):
        self.provider = self._get_provider()
        
    def _get_provider(self) -> BaseLLMProvider:
        provider_name = settings.LLM_DEFAULT_PROVIDER
        if provider_name == "openai":
            return OpenAIProvider(settings.LLM_OPENAI_API_KEY)
        elif provider_name == "anthropic": 
            return AnthropicProvider(settings.LLM_ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")
```

## Service Integration Specifications

### **ProcessingService Integration**
```python
# Uses LLM for core ticket generation
class ProcessingService:
    async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
        # 1. Load validated CSV data
        # 2. For each entity group:
        #    - Call llm_service.generate_ticket_content()
        #    - Create ticket records
        # 3. Call llm_service.generate_dependency_analysis() (placeholder in Phase 1)
        # 4. Create dependency records
```

### **UploadService Integration**  
```python
# Uses LLM for error explanations (placeholder in Phase 1)
class UploadService:
    async def explain_error(self, error_id: UUID) -> ErrorExplanationResponse:
        # Call llm_service.explain_error() 
        # Phase 1: Returns formatted original error
        # Phase 2: Returns LLM-generated explanation
```

### **Health Check Integration**
```python
# Processing endpoints use connectivity validation
@router.post("/api/processing/generate-tickets/{session_id}")
async def generate_tickets(session_id: UUID, llm_service: LLMService = Depends(get_llm_service)):
    # Pre-flight check
    health = await llm_service.validate_connectivity()
    if health["status"] != "healthy":
        raise HTTPException(503, f"LLM service unavailable: {health}")
```

## Dependency Injection Configuration

### **Environment Configuration**
```python
# app/core/config.py
class Settings(BaseSettings):
    LLM_DEFAULT_PROVIDER: str = "openai"
    LLM_ERROR_EXPLANATION_PROVIDER: str = "openai"  # Can differ for A/B testing
    LLM_OPENAI_API_KEY: str
    LLM_ANTHROPIC_API_KEY: str
    LLM_ENABLE_ERROR_EXPLANATIONS: bool = True  # Feature flag
```

### **Dependency Injection**
```python
# app/api/dependencies/external.py
@lru_cache()
def get_llm_service() -> LLMService:
    return LLMService()
    
def get_error_explanation_llm_service() -> LLMService:
    # Could return different provider for error explanations
    provider = settings.LLM_ERROR_EXPLANATION_PROVIDER
    return LLMService(provider_override=provider)
```

## Implementation Priority and Rationale

### **Why Full Interface with Phased Implementation?**

#### **1. Complete API Contract** 
- Services can depend on full interface immediately
- No need to change service signatures later
- Clear development roadmap

#### **2. Core Value Implementation**
- **Ticket generation is essential** - primary application value
- **Health checks prevent failures** - avoid expensive processing when LLM unavailable
- **Cost estimation builds trust** - users need transparency

#### **3. Smart Placeholders**
- **Dependency analysis**: Hardcoded Drupal rules work fine initially
- **Error explanations**: Formatted original errors sufficient for MVP
- **Future enhancement path clear**

### **What Claude Code Must Implement**

#### **Required (Core Value):**
- ✅ **Real LLM provider integration** (OpenAI/Anthropic)
- ✅ **Actual ticket content generation** 
- ✅ **Connectivity validation**
- ✅ **Cost estimation**

#### **Placeholder (Future Enhancement):**
- 📋 **Error explanations** - return formatted original error
- 📋 **Dependency analysis** - use hardcoded Drupal relationship rules

#### **Infrastructure:**
- ✅ **Provider abstraction** - support both OpenAI and Anthropic
- ✅ **Environment configuration** - flexible provider selection
- ✅ **Dependency injection** - proper service integration

## Success Criteria

### **Phase 1 (Claude Code Implementation)**
- ✅ LLM service generates actual ticket content using real AI models
- ✅ Processing workflow creates meaningful tickets from CSV data
- ✅ Health checks prevent processing when LLM services unavailable
- ✅ Cost estimation provides transparency to users
- ✅ Provider abstraction supports both OpenAI and Anthropic
- ✅ Error explanation endpoint works (with placeholder implementation)
- ✅ Dependency analysis works (with hardcoded rules)

### **Phase 2 (Future Enhancement)**
- 📋 LLM-powered error explanations provide user-friendly guidance
- 📋 Enhanced dependency analysis uses AI to detect complex relationships
- 📋 Advanced prompt optimization improves ticket quality
- 📋 Multi-provider load balancing optimizes costs and reliability

This specification resolves all ambiguity about LLM service scope while providing a clear implementation path for Claude Code that delivers immediate value with a foundation for future enhancement.