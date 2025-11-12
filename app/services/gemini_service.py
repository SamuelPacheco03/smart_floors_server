import google.generativeai as genai
from typing import Optional, Dict
import logging
from app.core.config import settings
from app.db.models.enums import Variable, AlertLevel

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None
        self.is_available = False
        self.model_name = None
        
        # Verificar si la API key está configurada (no vacía)
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY.strip())
                
                # Modelos disponibles en versión gratuita (en orden de preferencia)
                available_models = [
                    "gemini-1.5-flash",  # Modelo gratuito, rápido y eficiente
                    "gemini-1.5-flash-latest",  # Versión más reciente
                    "gemini-pro",  # Fallback si flash no funciona
                ]
                
                # Si el usuario especificó un modelo, intentarlo primero
                if settings.GEMINI_MODEL and settings.GEMINI_MODEL.strip():
                    available_models.insert(0, settings.GEMINI_MODEL.strip())
                
                # Intentar cada modelo hasta encontrar uno que funcione
                for model_name in available_models:
                    try:
                        logger.info(f"Intentando configurar modelo: {model_name}")
                        self.model = genai.GenerativeModel(model_name)
                        # Hacer una prueba rápida para verificar que funciona
                        test_response = self.model.generate_content("test")
                        self.is_available = True
                        self.model_name = model_name
                        logger.info(f"✅ Gemini AI configurado correctamente con modelo: {model_name}")
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ Modelo {model_name} no disponible: {e}")
                        continue
                
                # Si ningún modelo funcionó, listar modelos disponibles
                if not self.is_available:
                    try:
                        logger.info("Listando modelos disponibles...")
                        models = genai.list_models()
                        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                        logger.info(f"Modelos disponibles: {available}")
                        
                        # Intentar con el primer modelo disponible que contenga 'flash' o 'gemini'
                        for model in available:
                            if 'flash' in model.lower() or 'gemini' in model.lower():
                                try:
                                    # Extraer solo el nombre del modelo (sin 'models/')
                                    model_name = model.split('/')[-1] if '/' in model else model
                                    logger.info(f"Intentando con modelo disponible: {model_name}")
                                    self.model = genai.GenerativeModel(model_name)
                                    test_response = self.model.generate_content("test")
                                    self.is_available = True
                                    self.model_name = model_name
                                    logger.info(f"✅ Gemini AI configurado con modelo: {model_name}")
                                    break
                                except Exception as e:
                                    logger.warning(f"Error con {model_name}: {e}")
                                    continue
                    except Exception as e:
                        logger.error(f"❌ Error listando modelos: {e}")
                        
                if not self.is_available:
                    logger.error("❌ No se pudo configurar ningún modelo de Gemini. Usando recomendaciones predefinidas.")
                    
            except Exception as e:
                logger.error(f"❌ Error inicializando Gemini AI: {e}")
                self.model = None
        else:
            logger.warning("⚠️ GEMINI_API_KEY no configurada. Usando recomendaciones predefinidas.")
    
    def generate_recommendation(
        self,
        variable: Variable,
        level: AlertLevel,
        floor_number: int,
        current_value: float,
        historical_context: Optional[Dict] = None
    ) -> str:
        """
        Genera una recomendación accionable usando Gemini AI
        """
        if not self.is_available or not self.model:
            logger.debug("Usando recomendación de fallback (Gemini no disponible)")
            return self._fallback_recommendation(variable, level, floor_number, current_value)
        
        # Construir contexto para el prompt
        variable_name = {
            Variable.temperature: "temperatura",
            Variable.humidity: "humedad relativa",
            Variable.energy: "consumo de energía"
        }.get(variable, variable.value)
        
        level_name = {
            AlertLevel.info: "informativa",
            AlertLevel.medium: "media",
            AlertLevel.critical: "crítica"
        }.get(level, level.value)
        
        # Determinar unidad
        unit = "°C" if variable == Variable.temperature else "%" if variable == Variable.humidity else " kW"
        
        # Construir contexto histórico si está disponible
        context_text = ""
        if historical_context:
            if historical_context.get("trend") == "increasing":
                context_text = "\n- Tendencia: Los valores están aumentando."
            elif historical_context.get("trend") == "decreasing":
                context_text = "\n- Tendencia: Los valores están disminuyendo."
        
        # Prompt mejorado para Gemini
        prompt = f"""Eres un experto en gestión de edificios inteligentes. Genera UNA SOLA recomendación clara, específica y accionable.

CONTEXTO:
- Piso: {floor_number}
- Variable: {variable_name}
- Nivel de alerta: {level_name}
- Valor actual: {current_value}{unit}{context_text}

REQUISITOS ESTRICTOS:
1. La recomendación debe ser ESPECÍFICA y ACCIONABLE
2. DEBE incluir un tiempo estimado (ej: "en los próximos 15 min", "en la próxima hora", "inmediatamente")
3. DEBE mencionar el número del piso
4. Máximo 150 caracteres
5. Tono profesional pero directo
6. NO incluyas explicaciones, solo la recomendación

Ejemplos de formato correcto:
- "Ajustar setpoint del Piso {floor_number} a 24°C en los próximos 15 min."
- "Incrementar ventilación del Piso {floor_number}; revisar puertas/celosías."
- "Redistribuir carga eléctrica del Piso {floor_number} al 1 en la próxima hora."
- "Activar deshumidificación del Piso {floor_number} inmediatamente."

Genera SOLO la recomendación (sin comillas, sin explicaciones):"""

        try:
            logger.debug(f"Generando recomendación con Gemini ({self.model_name}) para Piso {floor_number}, {variable_name} = {current_value}{unit}")
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=100,
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE"
                    }
                ]
            )
            
            # Verificar finish_reason antes de acceder a response.text
            if not response.candidates:
                logger.warning("No se recibieron candidatos en la respuesta de Gemini")
                return self._fallback_recommendation(variable, level, floor_number, current_value)
            
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            
            # Mapeo de finish_reason
            finish_reasons = {
                0: "FINISH_REASON_UNSPECIFIED",
                1: "STOP",  # Éxito
                2: "MAX_TOKENS",  # Límite de tokens alcanzado
                3: "SAFETY",  # Bloqueado por seguridad
                4: "RECITATION",  # Problema de recitación
                5: "OTHER"
            }
            
            reason_name = finish_reasons.get(finish_reason, f"UNKNOWN({finish_reason})")
            
            if finish_reason != 1:  # Si no es STOP (éxito)
                logger.warning(f"⚠️ Gemini finish_reason: {reason_name} ({finish_reason})")
                if finish_reason == 3:  # SAFETY
                    logger.warning("Respuesta bloqueada por filtros de seguridad, usando fallback")
                elif finish_reason == 2:  # MAX_TOKENS
                    logger.warning("Límite de tokens alcanzado, intentando leer respuesta parcial")
                    # Intentar leer la respuesta parcial si existe
                    if candidate.content and candidate.content.parts:
                        recommendation = candidate.content.parts[0].text.strip()
                        if recommendation:
                            recommendation = recommendation.strip('"').strip("'").strip()
                            if len(recommendation) >= 10:
                                logger.info(f"✅ Usando respuesta parcial: {recommendation[:50]}...")
                                return recommendation[:300]
                return self._fallback_recommendation(variable, level, floor_number, current_value)
            
            # Si llegamos aquí, finish_reason es 1 (STOP) - éxito
            if not candidate.content or not candidate.content.parts:
                logger.warning("Respuesta exitosa pero sin contenido, usando fallback")
                return self._fallback_recommendation(variable, level, floor_number, current_value)
            
            recommendation = candidate.content.parts[0].text.strip()
            
            # Limpiar la respuesta (remover comillas si las tiene)
            recommendation = recommendation.strip('"').strip("'").strip()
            
            # Verificar que la recomendación tenga sentido
            if len(recommendation) < 10:
                logger.warning(f"Recomendación de Gemini muy corta: {recommendation}, usando fallback")
                return self._fallback_recommendation(variable, level, floor_number, current_value)
            
            # Limitar a 300 caracteres (límite de la BD)
            recommendation = recommendation[:300]
            logger.info(f"✅ Recomendación generada por Gemini: {recommendation[:50]}...")
            return recommendation
            
        except ValueError as e:
            # Manejar específicamente el error de response.text
            if "finish_reason" in str(e) or "Part" in str(e):
                logger.warning(f"⚠️ Respuesta bloqueada o incompleta de Gemini: {e}")
                logger.info("Usando recomendación de fallback")
                return self._fallback_recommendation(variable, level, floor_number, current_value)
            raise
        except Exception as e:
            logger.error(f"❌ Error generando recomendación con Gemini: {type(e).__name__}: {e}")
            logger.debug(f"Detalles del error: {str(e)}")
            # Si el error es de modelo no encontrado, marcar como no disponible
            if "NotFound" in str(e) or "404" in str(e):
                logger.warning("Modelo no encontrado, deshabilitando Gemini para esta sesión")
                self.is_available = False
            return self._fallback_recommendation(variable, level, floor_number, current_value)
    
    def _fallback_recommendation(
        self,
        variable: Variable,
        level: AlertLevel,
        floor_number: int,
        current_value: float
    ) -> str:
        """Recomendaciones de respaldo si Gemini no está disponible"""
        if variable == Variable.temperature:
            if level == AlertLevel.critical:
                return f"Ajustar setpoint del Piso {floor_number} a 24°C en los próximos 15 min."
            elif level == AlertLevel.medium:
                return f"Revisar sistema de climatización del Piso {floor_number} en la próxima hora."
            else:
                return f"Monitorear temperatura del Piso {floor_number}."
        
        elif variable == Variable.humidity:
            if level == AlertLevel.critical:
                if current_value > 80:
                    return f"Activar deshumidificación del Piso {floor_number} inmediatamente."
                else:
                    return f"Activar humidificación del Piso {floor_number} inmediatamente."
            elif level == AlertLevel.medium:
                return f"Ajustar control de humedad del Piso {floor_number} en la próxima hora."
            else:
                return f"Verificar humedad del Piso {floor_number}."
        
        elif variable == Variable.energy:
            if level == AlertLevel.critical:
                return f"Redistribuir carga eléctrica del Piso {floor_number} en la próxima hora."
            elif level == AlertLevel.medium:
                return f"Revisar consumo energético del Piso {floor_number}."
            else:
                return f"Monitorear energía del Piso {floor_number}."
        
        return f"Revisar {variable.value} del Piso {floor_number}."


gemini_service = GeminiService()
