"""State machine for MLX conversation flow.

Manages conversation states and transitions:
- IDLE: Waiting for user input
- LISTENING: Receiving audio/processing speech-to-text
- PROCESSING: LLM generating response
- SPEAKING: Text-to-speech output

Simple state machine following José Valim principles:
- Make states explicit
- Clear transition rules
- Easy to understand and debug
"""

import logging
from enum import Enum, auto
from typing import Optional, Callable
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Conversation states."""

    IDLE = auto()       # Waiting for input
    LISTENING = auto()  # Processing speech input
    PROCESSING = auto() # LLM thinking
    SPEAKING = auto()   # TTS output


@dataclass
class StateTransition:
    """Record of a state transition."""

    from_state: ConversationState
    to_state: ConversationState
    reason: str
    timestamp: float = field(default_factory=lambda: __import__('time').time())


class ConversationStateMachine:
    """State machine for conversation flow.

    Example:
        >>> sm = ConversationStateMachine()
        >>> sm.transition_to(ConversationState.LISTENING, "User started speaking")
        >>> print(sm.current_state)
        ConversationState.LISTENING
    """

    # Valid state transitions
    VALID_TRANSITIONS = {
        ConversationState.IDLE: {
            ConversationState.LISTENING,  # User starts speaking
        },
        ConversationState.LISTENING: {
            ConversationState.PROCESSING,  # Speech-to-text complete
            ConversationState.IDLE,        # User stopped (no speech detected)
        },
        ConversationState.PROCESSING: {
            ConversationState.SPEAKING,    # LLM response ready
            ConversationState.IDLE,        # Error or cancellation
        },
        ConversationState.SPEAKING: {
            ConversationState.IDLE,        # TTS complete
            ConversationState.LISTENING,   # User interruption
        },
    }

    def __init__(
        self,
        initial_state: ConversationState = ConversationState.IDLE,
        on_transition: Optional[Callable[[StateTransition], None]] = None,
    ):
        """Initialize state machine.

        Args:
            initial_state: Starting state (default: IDLE)
            on_transition: Optional callback called on each transition
        """
        self.current_state = initial_state
        self.on_transition = on_transition
        self.history: list[StateTransition] = []

        logger.info(f"State machine initialized: {initial_state.name}")

    def can_transition_to(self, target_state: ConversationState) -> bool:
        """Check if transition to target state is valid.

        Args:
            target_state: Desired state

        Returns:
            True if transition is allowed
        """
        if self.current_state == target_state:
            return True  # Already in target state

        valid_targets = self.VALID_TRANSITIONS.get(self.current_state, set())
        return target_state in valid_targets

    def transition_to(
        self,
        target_state: ConversationState,
        reason: str = "",
    ) -> bool:
        """Transition to new state.

        Args:
            target_state: Desired state
            reason: Human-readable reason for transition

        Returns:
            True if transition succeeded, False if invalid

        Example:
            >>> success = sm.transition_to(
            ...     ConversationState.PROCESSING,
            ...     "STT completed, sending to LLM"
            ... )
        """
        # Skip if already in target state
        if self.current_state == target_state:
            logger.debug(f"Already in state: {target_state.name}")
            return True

        # Validate transition
        if not self.can_transition_to(target_state):
            logger.warning(
                f"Invalid transition: {self.current_state.name} → {target_state.name}"
            )
            return False

        # Record transition
        transition = StateTransition(
            from_state=self.current_state,
            to_state=target_state,
            reason=reason,
        )
        self.history.append(transition)

        # Update state
        old_state = self.current_state
        self.current_state = target_state

        logger.info(f"State: {old_state.name} → {target_state.name} ({reason})")

        # Notify callback
        if self.on_transition:
            try:
                self.on_transition(transition)
            except Exception as e:
                logger.error(f"Error in transition callback: {e}")

        return True

    def force_transition_to(self, target_state: ConversationState, reason: str = ""):
        """Force transition to any state (bypass validation).

        Use for error recovery or manual control only.

        Args:
            target_state: Desired state
            reason: Reason for forced transition
        """
        logger.warning(
            f"FORCED transition: {self.current_state.name} → {target_state.name} ({reason})"
        )

        transition = StateTransition(
            from_state=self.current_state,
            to_state=target_state,
            reason=f"FORCED: {reason}",
        )
        self.history.append(transition)
        self.current_state = target_state

    def reset(self):
        """Reset to IDLE state."""
        self.transition_to(ConversationState.IDLE, "Reset requested")

    def get_history(self, last_n: Optional[int] = None) -> list[StateTransition]:
        """Get transition history.

        Args:
            last_n: Return only last N transitions (default: all)

        Returns:
            List of transitions
        """
        if last_n is None:
            return self.history.copy()
        return self.history[-last_n:]

    def __repr__(self) -> str:
        """String representation."""
        return f"ConversationStateMachine(current={self.current_state.name})"
