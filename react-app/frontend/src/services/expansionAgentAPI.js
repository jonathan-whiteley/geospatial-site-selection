/**
 * Expansion Intelligence Agent API Client
 * Integrates with Databricks Multi-Agent Serving endpoint
 */
import { useState, useEffect, useCallback } from 'react'

class ExpansionAgentAPI {
  constructor() {
    this.endpointUrl = '/api/agent/chat'
    this.healthEndpoint = '/api/agent/health'
    this.sessionId = this.generateSessionId()
    this.conversationHistory = []

    this.config = {
      timeout: 60000,
      retryAttempts: 2,
      retryDelay: 1000,
      maxHistoryLength: 20,
    }
  }

  async sendMessage(message, context = {}) {
    if (!message?.trim()) {
      throw new Error('Message cannot be empty')
    }

    // Add to conversation history
    this.conversationHistory.push({
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    })

    // Trim history if needed
    if (this.conversationHistory.length > this.config.maxHistoryLength) {
      this.conversationHistory = this.conversationHistory.slice(
        -this.config.maxHistoryLength
      )
    }

    try {
      const response = await this._makeRequest({
        messages: [{ role: 'user', content: message }],
        context: {
          ...context,
          session_id: this.sessionId,
          conversation_history: this.conversationHistory.slice(-5),
        },
      })

      // Extract text from ResponsesAgent format
      const responseText = this._extractResponseText(response)

      // Add to history
      this.conversationHistory.push({
        type: 'agent',
        content: responseText,
        timestamp: new Date().toISOString(),
      })

      return {
        success: true,
        message: responseText,
        metadata: response,
        timestamp: new Date().toISOString(),
        sessionId: this.sessionId,
      }
    } catch (error) {
      console.error('Agent API Error:', error)
      return {
        success: false,
        error: error.message,
        message: this._getErrorMessage(error),
        timestamp: new Date().toISOString(),
        sessionId: this.sessionId,
      }
    }
  }

  async checkHealth() {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000)

      const response = await fetch(this.healthEndpoint, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        return {
          status: data.auth_configured ? 'healthy' : 'unconfigured',
          endpoint: data.endpoint,
          timestamp: new Date().toISOString(),
        }
      }

      return {
        status: 'unhealthy',
        error: `HTTP ${response.status}`,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      return {
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString(),
      }
    }
  }

  clearHistory() {
    this.conversationHistory = []
    this.sessionId = this.generateSessionId()
  }

  getHistory() {
    return [...this.conversationHistory]
  }

  async _makeRequest(payload, attempt = 1) {
    const controller = new AbortController()
    const timeoutId = setTimeout(
      () => controller.abort(),
      this.config.timeout
    )

    try {
      const response = await fetch(this.endpointUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Unknown error')
      }

      return data.response
    } catch (error) {
      clearTimeout(timeoutId)
      if (attempt < this.config.retryAttempts && this._shouldRetry(error)) {
        await this._delay(this.config.retryDelay * attempt)
        return this._makeRequest(payload, attempt + 1)
      }
      throw error
    }
  }

  _extractResponseText(response) {
    // Handle Multi-Agent ResponsesAgent format
    if (response?.output && Array.isArray(response.output)) {
      const textOutputs = response.output
        .filter((item) => item.type === 'message' && item.content)
        .flatMap((item) => item.content)
        .filter((content) => content.type === 'output_text')
        .map((content) => content.text)
        .join('\n\n')

      if (textOutputs) return this._cleanAgentResponse(textOutputs)
    }

    // Handle simple message format
    if (response?.message) return this._cleanAgentResponse(response.message)
    if (response?.text) return this._cleanAgentResponse(response.text)

    // Handle choices format (like OpenAI)
    if (response?.choices?.[0]?.message?.content) {
      return this._cleanAgentResponse(response.choices[0].message.content)
    }

    // Fallback for string response
    if (typeof response === 'string') return this._cleanAgentResponse(response)

    return 'No response received'
  }

  _cleanAgentResponse(text) {
    if (!text) return text

    // Remove tool/agent name tags like <name>agent-xyz</name> (including multiline)
    let cleaned = text.replace(/<name>[\s\S]*?<\/name>/gi, '')

    // Remove tool_use blocks with XML-like syntax
    cleaned = cleaned.replace(/<tool_use>[\s\S]*?<\/tool_use>/gi, '')

    // Remove thinking blocks
    cleaned = cleaned.replace(/<thinking>[\s\S]*?<\/thinking>/gi, '')

    // Remove function_call blocks
    cleaned = cleaned.replace(/<function_call>[\s\S]*?<\/function_call>/gi, '')

    // Remove tool_result blocks
    cleaned = cleaned.replace(/<tool_result>[\s\S]*?<\/tool_result>/gi, '')

    // Remove tool call references like [tool:xyz] or {tool:xyz}
    cleaned = cleaned.replace(/\[tool:[^\]]*\]/g, '')
    cleaned = cleaned.replace(/\{tool:[^}]*\}/g, '')

    // Remove lines that are just agent/tool identifiers
    cleaned = cleaned.replace(/^.*agent-.*-demo.*$/gim, '')
    cleaned = cleaned.replace(/^.*genie-ma-.*$/gim, '')

    // Clean up excessive whitespace and newlines
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim()

    return cleaned
  }

  _shouldRetry(error) {
    return (
      error.name === 'AbortError' ||
      error.name === 'TypeError' ||
      error.message.includes('fetch') ||
      error.message.includes('5')
    )
  }

  _getErrorMessage(error) {
    if (error.name === 'AbortError') {
      return '**Request Timeout**\n\nThe query is taking longer than expected. Try a simpler question.'
    }
    if (error.message.includes('401') || error.message.includes('403')) {
      return '**Authentication Error**\n\nUnable to access the analytics service. Please contact support.'
    }
    if (error.message.includes('5')) {
      return '**Service Error**\n\nThe analytics service is experiencing issues. Please try again.'
    }
    return `**Error**\n\n${error.message}`
  }

  generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
  }

  _delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }
}

/**
 * React Hook for Expansion Agent Integration
 */
export const useExpansionAgent = () => {
  const [agent] = useState(() => new ExpansionAgentAPI())
  const [connectionStatus, setConnectionStatus] = useState('disconnected')
  const [lastHealthCheck, setLastHealthCheck] = useState(null)

  useEffect(() => {
    const checkHealth = async () => {
      setConnectionStatus('connecting')
      const health = await agent.checkHealth()
      setConnectionStatus(health.status === 'healthy' ? 'connected' : 'error')
      setLastHealthCheck(health)
    }

    checkHealth()
    const interval = setInterval(checkHealth, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [agent])

  const sendMessage = useCallback(
    async (message, context = {}) => agent.sendMessage(message, context),
    [agent]
  )

  const clearHistory = useCallback(() => agent.clearHistory(), [agent])
  const getHistory = useCallback(() => agent.getHistory(), [agent])

  return {
    sendMessage,
    clearHistory,
    getHistory,
    connectionStatus,
    lastHealthCheck,
    isAvailable: connectionStatus === 'connected',
  }
}

export default ExpansionAgentAPI
