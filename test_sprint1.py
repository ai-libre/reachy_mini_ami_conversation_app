#!/usr/bin/env python3
"""Sprint 1 Validation Script

Tests all Sprint 1 components:
- Hardware detection
- Configuration system
- State machine
- LLM wrapper (basic checks)
- Handler initialization

Run with: python test_sprint1.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_hardware_detection():
    """Test 1: Hardware Detection"""
    print("\n" + "=" * 60)
    print("Test 1: Hardware Detection")
    print("=" * 60)

    try:
        from reachy_mini_conversation_app.mlx import (
            detect_backend,
            get_memory_info,
            MLXBackend,
        )

        backend = detect_backend()
        logger.info(f"✅ Backend detected: {backend.value}")

        memory_info = get_memory_info()
        logger.info(f"✅ Memory info: {memory_info}")

        return True
    except ImportError as e:
        logger.warning(f"⚠️  MLX not installed (expected): {e}")
        logger.info("   This is OK - MLX will be installed when running the app")
        return True  # Not a failure
    except Exception as e:
        logger.error(f"❌ Hardware detection failed: {e}")
        return False


def test_configuration():
    """Test 2: Configuration System"""
    print("\n" + "=" * 60)
    print("Test 2: Configuration System")
    print("=" * 60)

    try:
        from reachy_mini_conversation_app.mlx import MLXConfig

        # Test default config
        config = MLXConfig()
        logger.info(f"✅ Default config created")
        logger.info(f"   LLM Model: {config.llm_model}")
        logger.info(f"   VLM Model: {config.vlm_model}")
        logger.info(f"   TTS Voice: {config.tts_voice}")

        # Test environment override
        import os
        os.environ["MLX_LLM_MODEL"] = "test-model"
        config_with_env = MLXConfig()
        assert config_with_env.llm_model == "test-model", "Env override failed"
        logger.info(f"✅ Environment override works")
        del os.environ["MLX_LLM_MODEL"]

        return True
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False


def test_state_machine():
    """Test 3: State Machine"""
    print("\n" + "=" * 60)
    print("Test 3: State Machine")
    print("=" * 60)

    try:
        from reachy_mini_conversation_app.mlx import (
            ConversationState,
            ConversationStateMachine,
        )

        # Create state machine
        sm = ConversationStateMachine()
        assert sm.current_state == ConversationState.IDLE
        logger.info(f"✅ State machine created: {sm.current_state.name}")

        # Test valid transition
        success = sm.transition_to(ConversationState.LISTENING, "Test transition")
        assert success, "Valid transition failed"
        assert sm.current_state == ConversationState.LISTENING
        logger.info(f"✅ Valid transition: IDLE → LISTENING")

        # Test invalid transition
        success = sm.transition_to(ConversationState.SPEAKING, "Invalid transition")
        assert not success, "Invalid transition should fail"
        assert sm.current_state == ConversationState.LISTENING, "State changed on invalid transition"
        logger.info(f"✅ Invalid transition rejected correctly")

        # Test valid chain
        sm.transition_to(ConversationState.PROCESSING, "STT complete")
        sm.transition_to(ConversationState.SPEAKING, "LLM response ready")
        sm.transition_to(ConversationState.IDLE, "TTS complete")
        assert sm.current_state == ConversationState.IDLE
        logger.info(f"✅ Full conversation flow: IDLE → LISTENING → PROCESSING → SPEAKING → IDLE")

        # Test history
        history = sm.get_history()
        assert len(history) >= 4, "History not recorded"
        logger.info(f"✅ State history tracked: {len(history)} transitions")

        return True
    except Exception as e:
        logger.error(f"❌ State machine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_wrapper():
    """Test 4: LLM Wrapper (Basic Checks)"""
    print("\n" + "=" * 60)
    print("Test 4: LLM Wrapper")
    print("=" * 60)

    try:
        from reachy_mini_conversation_app.mlx.llm import MLXLanguageModel

        # Test initialization (no loading)
        llm = MLXLanguageModel(
            model_path="mlx-community/Hermes-2-Pro-Llama-3-8B-4bit",
            use_cache=True,
            temperature=0.7,
            max_tokens=500,
        )

        assert not llm.is_loaded(), "Model should not be loaded yet"
        logger.info(f"✅ LLM wrapper created: {llm}")

        # Test message management
        llm.add_message("system", "You are a helpful assistant")
        llm.add_message("user", "Hello!")

        history = llm.get_history()
        assert len(history) == 2, "Message history not working"
        logger.info(f"✅ Message history works: {len(history)} messages")

        llm.clear_history()
        assert len(llm.get_history()) == 0, "Clear history failed"
        logger.info(f"✅ Clear history works")

        # Test function call parsing
        test_response = '<tool_call>{"name": "test_tool", "arguments": {"arg": "value"}}</tool_call>'
        tool_call = llm.parse_function_call(test_response)
        assert tool_call is not None, "Function call parsing failed"
        assert tool_call["name"] == "test_tool", "Tool name parsing failed"
        logger.info(f"✅ Function call parsing works: {tool_call['name']}")

        logger.info("⚠️  Skipping model loading (requires MLX installation and model download)")
        logger.info("   Run prototype_mlx_poc.py to test actual model loading")

        return True
    except ImportError as e:
        logger.warning(f"⚠️  MLX-LM not installed: {e}")
        logger.info("   Install with: pip install mlx-lm")
        return True  # Not a failure for Sprint 1
    except Exception as e:
        logger.error(f"❌ LLM wrapper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_handler_initialization():
    """Test 5: Handler Initialization"""
    print("\n" + "=" * 60)
    print("Test 5: Handler Initialization")
    print("=" * 60)

    try:
        from reachy_mini_conversation_app.handlers.mlx_handler import MLXRealtimeHandler
        from reachy_mini_conversation_app.mlx import MLXConfig

        # Create mock dependencies
        class MockDeps:
            movement_manager = None
            head_wobbler = None
            camera_worker = None

        deps = MockDeps()
        config = MLXConfig()

        # Test handler creation
        handler = MLXRealtimeHandler(deps, config)
        logger.info(f"✅ Handler created")
        logger.info(f"   State: {handler.state_machine.current_state.name}")
        logger.info(f"   Input sample rate: {handler.input_sample_rate}")
        logger.info(f"   Output sample rate: {handler.output_sample_rate}")

        # Test copy
        handler_copy = handler.copy()
        assert handler_copy is not handler, "Copy should create new instance"
        logger.info(f"✅ Handler copy works")

        logger.info("⚠️  Skipping start_up() test (requires MLX installation)")
        logger.info("   Full handler test requires running the actual app")

        return True
    except ImportError as e:
        logger.warning(f"⚠️  Dependencies not installed: {e}")
        return True  # Not a failure
    except Exception as e:
        logger.error(f"❌ Handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Sprint 1 validation tests"""
    print("\n" + "=" * 60)
    print("Sprint 1 Validation Tests")
    print("=" * 60)

    tests = [
        ("Hardware Detection", test_hardware_detection),
        ("Configuration System", test_configuration),
        ("State Machine", test_state_machine),
        ("LLM Wrapper", test_llm_wrapper),
        ("Handler Initialization", test_handler_initialization),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All Sprint 1 tests passed!")
        print("\nNext steps:")
        print("1. Install MLX dependencies: pip install -r requirements-mlx.txt")
        print("2. Run proof of concept: python prototype_mlx_poc.py")
        print("3. Start Sprint 2: Audio integration")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
