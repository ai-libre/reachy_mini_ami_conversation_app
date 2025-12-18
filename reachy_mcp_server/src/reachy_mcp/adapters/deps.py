"""
Dependency injection for robot components.

Creates and manages shared robot dependencies used across tools and resources.
"""

from dataclasses import dataclass
from typing import Optional

from reachy_mini import ReachyMini

# Import existing components
from reachy_mini_conversation_app.camera_worker import CameraWorker
from reachy_mini_conversation_app.moves import MovementManager
from reachy_mini_conversation_app.tools.core_tools import ToolDependencies
from reachy_mini_conversation_app.vision.processors import VisionManager, VisionProcessor

from ..config import get_config
from ..utils import get_logger

logger = get_logger("adapters.deps")


@dataclass
class RobotDependencies:
    """
    Container for all robot-related dependencies.

    This provides clean dependency injection for tools and resources.
    """

    robot: ReachyMini
    movement_manager: MovementManager
    camera_worker: Optional[CameraWorker]
    vision_manager: Optional[VisionManager]

    # Original ToolDependencies for existing tool reuse
    tool_deps: ToolDependencies

    def __post_init__(self) -> None:
        """Validate dependencies after initialization."""
        if not isinstance(self.robot, ReachyMini):
            raise TypeError(f"Expected ReachyMini, got {type(self.robot)}")

        if not isinstance(self.movement_manager, MovementManager):
            raise TypeError(f"Expected MovementManager, got {type(self.movement_manager)}")

    def is_camera_available(self) -> bool:
        """Check if camera is available and functional."""
        return self.camera_worker is not None

    def is_vision_available(self) -> bool:
        """Check if vision processing is available."""
        return self.vision_manager is not None


def create_robot_dependencies() -> RobotDependencies:
    """
    Create and initialize robot dependencies.

    This function sets up all necessary robot components based on configuration.

    Returns:
        RobotDependencies: Initialized dependencies

    Raises:
        RobotConnectionError: If cannot connect to robot
        ConfigurationError: If configuration is invalid
    """
    config = get_config()

    logger.info("Initializing robot dependencies...")

    # Connect to robot (or create mock)
    if config.mock_robot:
        logger.warning("Using MOCK robot (no actual hardware)")
        robot = _create_mock_robot()
    else:
        logger.info(f"Connecting to robot at {config.robot_host}:{config.robot_port}")
        try:
            robot = ReachyMini(host=config.robot_host, port=config.robot_port)
            logger.info("✓ Robot connected successfully")
        except Exception as e:
            from ..utils import RobotConnectionError

            logger.error(f"Failed to connect to robot: {e}")
            raise RobotConnectionError(
                f"Cannot connect to robot at {config.robot_host}:{config.robot_port}",
                {"error": str(e)},
            ) from e

    # Initialize MovementManager
    logger.info("Initializing MovementManager...")
    movement_manager = MovementManager(robot)
    movement_manager.start()
    logger.info("✓ MovementManager started")

    # Initialize CameraWorker (if enabled)
    camera_worker: Optional[CameraWorker] = None
    if config.enable_camera:
        logger.info("Initializing CameraWorker...")
        try:
            # Setup camera worker based on config
            head_tracker = None
            if config.face_tracking_mode.value != "disabled":
                logger.info(f"Setting up {config.face_tracking_mode.value} face tracking...")
                head_tracker = _create_head_tracker(config.face_tracking_mode.value)

            camera_worker = CameraWorker(robot, head_tracker=head_tracker)
            camera_worker.start()
            logger.info("✓ CameraWorker started")
        except Exception as e:
            logger.warning(f"Camera initialization failed: {e}")
            logger.warning("Continuing without camera support")
            camera_worker = None
    else:
        logger.info("Camera disabled by configuration")

    # Initialize VisionManager (if local vision enabled)
    vision_manager: Optional[VisionManager] = None
    if config.use_local_vision:
        logger.info("Initializing local vision...")
        try:
            vision_processor = VisionProcessor(model_name=config.local_vision_model)
            vision_manager = VisionManager(
                camera_worker=camera_worker, vision_processor=vision_processor
            )
            # Note: VisionManager is typically not started automatically
            # It's used on-demand for vision processing
            logger.info("✓ Local vision initialized")
        except Exception as e:
            logger.warning(f"Vision initialization failed: {e}")
            logger.warning("Continuing without local vision (will use cloud if available)")
            vision_manager = None
    else:
        logger.info("Using cloud vision (GPT-4V)")

    # Create ToolDependencies for existing tool reuse
    tool_deps = ToolDependencies(
        robot=robot,
        movement_manager=movement_manager,
        camera_worker=camera_worker,
        vision_manager=vision_manager,
    )

    # Bundle into RobotDependencies
    deps = RobotDependencies(
        robot=robot,
        movement_manager=movement_manager,
        camera_worker=camera_worker,
        vision_manager=vision_manager,
        tool_deps=tool_deps,
    )

    logger.info("✓ All robot dependencies initialized successfully")
    return deps


def _create_mock_robot() -> ReachyMini:
    """
    Create a mock robot for testing without hardware.

    Returns:
        Mock ReachyMini instance
    """
    from unittest.mock import MagicMock

    logger.warning("Creating mock robot - NO ACTUAL HARDWARE CONTROL")

    mock_robot = MagicMock(spec=ReachyMini)
    mock_robot.get_joint_positions.return_value = {
        "neck_pitch": 0.0,
        "neck_yaw": 0.0,
        "neck_roll": 0.0,
        "l_antenna": 0.0,
        "r_antenna": 0.0,
    }
    mock_robot.set_target.return_value = None

    return mock_robot


def _create_head_tracker(mode: str):
    """
    Create head tracker based on mode.

    Args:
        mode: Tracking mode (yolo or mediapipe)

    Returns:
        Head tracker instance
    """
    if mode == "yolo":
        from reachy_mini_conversation_app.vision.yolo_head_tracker import YoloHeadTracker

        return YoloHeadTracker()
    elif mode == "mediapipe":
        from reachy_mini_toolbox.mediapipe import HeadTracker

        return HeadTracker()
    else:
        raise ValueError(f"Unknown tracking mode: {mode}")


def cleanup_robot_dependencies(deps: RobotDependencies) -> None:
    """
    Cleanup robot dependencies on shutdown.

    Args:
        deps: Dependencies to cleanup
    """
    logger.info("Cleaning up robot dependencies...")

    # Stop components in reverse order
    if deps.vision_manager:
        try:
            deps.vision_manager.stop()
            logger.info("✓ VisionManager stopped")
        except Exception as e:
            logger.error(f"Error stopping VisionManager: {e}")

    if deps.camera_worker:
        try:
            deps.camera_worker.stop()
            logger.info("✓ CameraWorker stopped")
        except Exception as e:
            logger.error(f"Error stopping CameraWorker: {e}")

    try:
        deps.movement_manager.stop()
        logger.info("✓ MovementManager stopped")
    except Exception as e:
        logger.error(f"Error stopping MovementManager: {e}")

    # Disconnect robot
    try:
        if hasattr(deps.robot, "disconnect"):
            deps.robot.disconnect()
        logger.info("✓ Robot disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting robot: {e}")

    logger.info("✓ Cleanup complete")
