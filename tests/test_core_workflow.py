r"""Core smoke tests for parser, simulator, CAM, and UI wiring.

Run from project root:
    D:\python\python.exe tests\test_core_workflow.py
"""

from __future__ import annotations

import os
import sys

import ezdxf
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLCONFIGDIR", str(Path(".runtime-cache/matplotlib").resolve()))

from PySide6.QtWidgets import QApplication

from core.cam_generator import CamGenerator, MILLING_MODE
from core.dxf_reader import ALL_LAYERS_LABEL, DxfLine, DxfPolyline, DxfReadResult, DxfReader
from core.gcode_parser import GCodeParser
from core.resource_utils import read_text_with_fallback
from core.simulator import GCodeSimulator
from core.toolpath import ToolpathArc, ToolpathPoint
from ui.main_window import MainWindow
from ui.simulation_runner import SimulationRunner
from ui.demo_effect import IMAGE_CANDIDATES


_APP = QApplication.instance() or QApplication([])


def _default_cam_parameters(layer_filter: str = ALL_LAYERS_LABEL):
    return __import__("core.toolpath", fromlist=["CamParameters"]).CamParameters(
        tool_diameter=6.0,
        spindle_speed=12000,
        feed_rate=300,
        cutting_depth=-1.0,
        safe_height=5.0,
        machining_mode=MILLING_MODE,
        contour_direction="??",
        zero_origin=False,
        arc_output="????",
        layer_filter=layer_filter,
        cutter_compensation="none",
    )


def test_incremental_coordinates() -> None:
    code = """
G21
G90
G0 X0 Y0 Z0
G91
G1 X10 Y0 F600
G1 X0 Y5
G90
G1 X0 Y0
"""
    parsed = GCodeParser().parse(code)
    result = GCodeSimulator().simulate(parsed, plane="XY")
    assert result.final_position.x == 0.0
    assert result.final_position.y == 0.0
    assert any(cmd.command == "G91" for cmd in parsed.commands)
    linear_ends = [(seg.end_x, seg.end_y) for seg in result.segments if seg.move_type == "linear"]
    assert (10.0, 0.0) in linear_ends
    assert (10.0, 5.0) in linear_ends


def test_r_arc_and_radius_warning() -> None:
    parsed = GCodeParser().parse("G17\nG0 X0 Y0\nG2 X10 Y0 R5\nG2 X20 Y0 I1 J0\n")
    result = GCodeSimulator().simulate(parsed, plane="XY")
    assert any(seg.move_type == "arc" and seg.points for seg in result.segments)
    assert result.warnings, "mismatched I/J arc should create a simulation warning"


def test_r_arc_does_not_warn_about_missing_ijk() -> None:
    parsed = GCodeParser().parse("G17\nG0 X0 Y0\nG2 X10 Y0 R5\n")
    assert parsed.warnings == []


def test_arc_missing_center_or_radius_warning_is_readable() -> None:
    parsed = GCodeParser().parse("G17\nG0 X0 Y0\nG2 X10 Y0\n")
    assert parsed.warnings == ["\u7b2c 3 \u884c\uff1a\u5706\u5f27\u7f3a\u5c11 I/J/K \u5706\u5fc3\u504f\u79fb\u6216 R \u534a\u5f84\u53c2\u6570"]


def test_arc_missing_endpoint_warning_is_readable() -> None:
    parsed = GCodeParser().parse("G17\nG0 X0 Y0\nG2\n")
    assert parsed.warnings == [
        "\u7b2c 3 \u884c\uff1a\u5706\u5f27\u7f3a\u5c11 I/J/K \u5706\u5fc3\u504f\u79fb\u6216 R \u534a\u5f84\u53c2\u6570\uff1b\u7b2c 3 \u884c\uff1a\u5706\u5f27\u7f3a\u5c11\u7ec8\u70b9\u5750\u6807"
    ]


def test_ijk_full_circle_without_endpoint_is_valid() -> None:
    parsed = GCodeParser().parse("G17\nG0 X0 Y0\nG2 I5 J0\n")
    assert parsed.warnings == []


def test_turning_arc_i_uses_radius_coordinate() -> None:
    arc = ToolpathArc(
        start=ToolpathPoint(0.0, 10.0),
        end=ToolpathPoint(10.0, 0.0),
        center=ToolpathPoint(0.0, 0.0),
        clockwise=True,
    )
    line = CamGenerator()._turning_arc_command_xz(arc)
    assert "X0" in line
    assert "Z10" in line
    assert "I-10" in line
    assert "I-20" not in line


def test_runner_uses_segment_positions() -> None:
    parsed = GCodeParser().parse("G17\nG0 X0 Y0 Z5\nG1 X20 Y0 Z-1 F300\nG91\nG1 X0 Y10\n")
    result = GCodeSimulator().simulate(parsed, plane="XY")
    runner = SimulationRunner()
    runner.load(parsed, result)
    positions = runner.get_real_positions()
    assert positions[0] == (0.0, 0.0, 5.0)
    assert positions[-1] == (20.0, 10.0, -1.0)
    assert runner._segment_start_times == sorted(runner._segment_start_times)


def test_empty_runner_play_does_not_enter_playing_state() -> None:
    """空 runner 调用 play() 不应进入 playing 状态。"""
    runner = SimulationRunner()
    runner.play()
    assert not runner.is_playing()
    assert runner.total_duration() == 0.0


def test_clear_then_play_keeps_runner_idle() -> None:
    """load 后 clear 再 play，runner 应保持非播放状态且无残留数据。"""
    parsed = GCodeParser().parse("G0 X0 Y0 Z5\nG1 X10 F300\n")
    result = GCodeSimulator().simulate(parsed, plane="XY")
    runner = SimulationRunner()
    runner.load(parsed, result)
    assert runner.total_duration() > 0.0

    runner.clear()
    assert runner.total_duration() == 0.0
    assert runner.get_real_positions() == []

    runner.play()
    assert not runner.is_playing()


def test_start_simulation_with_no_motion_clears_old_runner() -> None:
    """先跑有效 G代码，再输入只有设置指令的内容，runner 应被彻底清空。"""
    window = MainWindow()
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X10 F300\n")
    window._start_simulation()
    assert window.simulation_runner.total_duration() > 0.0

    # 只有设置指令，无运动指令
    window.editor.set_text("G21\nG90\nM3\n")
    window._start_simulation()
    assert window.simulation_runner.total_duration() == 0.0
    assert not window.simulation_runner.is_playing()
    assert window.simulation_runner.get_real_positions() == []
    window.close()


def test_start_simulation_with_empty_editor_clears_old_runner() -> None:
    """先跑有效 G代码，再清空编辑器点开始仿真，runner 应被彻底清空。"""
    window = MainWindow()
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X10 F300\n")
    window._start_simulation()
    assert window.simulation_runner.total_duration() > 0.0

    window.editor.set_text("")
    window._start_simulation()
    assert window.simulation_runner.total_duration() == 0.0
    assert not window.simulation_runner.is_playing()
    assert window.simulation_runner.get_real_positions() == []
    window.close()


def test_simulation_summary_uses_runner_duration() -> None:
    window = MainWindow()
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X600 Y0 Z-1 F60\n")
    window._start_simulation()

    assert round(window.simulation_runner.total_duration()) == 600
    assert window.project_navigator.time_metric.text() == "00:10:00"
    assert window.timeline_panel.remaining_label.text() == "00:10:00"
    window.simulation_runner.stop()
    window.gl_canvas.stop_animation()
    window.close()


def test_build_script_uses_portable_python_launcher() -> None:
    script = Path("build_exe.bat").read_text(encoding="utf-8")
    assert r"D:\python\python.exe" not in script
    assert "where python" in script
    assert "where py" in script


def test_read_text_with_fallback_handles_chinese_windows_files() -> None:
    path = Path(".runtime-cache/gb18030_sample.nc")
    expected = "G1 X1 Y1 ; ????"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(expected.encode("gb18030"))
    assert read_text_with_fallback(path) == expected


def test_dxf_reader_preserves_layers_and_filters_geometry() -> None:
    path = Path(".runtime-cache/layer_filter_sample.dxf")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "OUTER"})
    msp.add_line((0, 5), (5, 5), dxfattribs={"layer": "INNER"})
    doc.saveas(path)

    result = DxfReader().read(path)

    assert result.layers == ["INNER", "OUTER"]
    assert result.filtered_by_layer("OUTER").entity_count == 1
    assert result.filtered_by_layer("OUTER").lines[0].layer == "OUTER"


def test_dxf_reader_expands_insert_and_spline() -> None:
    path = Path(".runtime-cache/insert_spline_sample.dxf")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    block = doc.blocks.new(name="CUT_BLOCK")
    block.add_line((0, 0), (4, 0), dxfattribs={"layer": "BLOCK_LAYER"})
    msp = doc.modelspace()
    msp.add_blockref("CUT_BLOCK", (10, 2), dxfattribs={"layer": "INSERT_LAYER"})
    msp.add_spline([(0, 0), (2, 3), (4, 0)], dxfattribs={"layer": "SPLINE_LAYER"})
    doc.saveas(path)

    result = DxfReader().read(path)

    assert any(line.layer == "INSERT_LAYER" for line in result.lines)
    assert any(polyline.layer == "SPLINE_LAYER" and len(polyline.points) >= 2 for polyline in result.polylines)


def test_cam_generation_respects_selected_layer() -> None:
    geometry = DxfReadResult(
        lines=[
            DxfLine(0.0, 0.0, 5.0, 0.0, "CUT"),
            DxfLine(0.0, 5.0, 5.0, 5.0, "SKIP"),
        ]
    )
    params = _default_cam_parameters(layer_filter="CUT")

    generated = CamGenerator().generate(geometry, params)

    assert generated.entity_count == 1
    assert generated.path_count == 1
    assert "Y5" not in generated.text


def test_milling_cutter_compensation_offsets_closed_contour() -> None:
    geometry = DxfReadResult(
        polylines=[
            DxfPolyline(
                points=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
                is_closed=True,
                layer="CUT",
            )
        ]
    )
    params = _default_cam_parameters()
    params = type(params)(**{**params.__dict__, "tool_diameter": 2.0, "cutter_compensation": "left"})

    generated = CamGenerator().generate(geometry, params)

    assert "X1 Y1" in generated.text
    assert "X9 Y1" in generated.text
    assert "X10 Y0" not in generated.text


def test_main_window_populates_layer_filter_from_dxf() -> None:
    path = Path(".runtime-cache/window_layer_sample.dxf")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "CUT"})
    msp.add_line((0, 5), (10, 5), dxfattribs={"layer": "SKIP"})
    doc.saveas(path)

    window = MainWindow()
    window._load_dxf_file(path)
    combo_values = [window.control_panel.layer_filter_input.itemText(i) for i in range(window.control_panel.layer_filter_input.count())]

    assert combo_values == [ALL_LAYERS_LABEL, "CUT", "SKIP"]
    window.close()


def test_project_tree_and_operation_table_use_real_data() -> None:
    path = Path(".runtime-cache/project_tree_sample.dxf")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "CUT"})
    msp.add_line((0, 5), (10, 5), dxfattribs={"layer": "SKIP"})
    doc.saveas(path)

    window = MainWindow()
    window._load_dxf_file(path)
    root = window.project_navigator.project_tree.topLevelItem(0)
    tree_texts: list[str] = []

    def collect(item) -> None:
        tree_texts.append(item.text(0))
        for index in range(item.childCount()):
            collect(item.child(index))

    collect(root)

    assert path.name in root.text(0)
    assert any("CUT" in text for text in tree_texts)
    assert any("SKIP" in text for text in tree_texts)

    window._generate_gcode()
    assert window.project_navigator.operation_table.rowCount() == 2
    assert window.project_navigator.operation_table.item(0, 0).text() == "1"
    assert window.project_navigator.operation_table.item(1, 0).text() == "2"
    window.close()


def test_demo_image_candidates_stay_under_assets() -> None:
    assert IMAGE_CANDIDATES[0] == Path("assets/武陆逊.png")
    assert all(p.parts[0] == "assets" for p in IMAGE_CANDIDATES)


def test_main_window_milling_and_turning_modes() -> None:
    window = MainWindow()
    window.control_panel.machining_mode_input.setCurrentIndex(0)
    assert window.control_panel.parameters().machining_mode == "铣削模式"
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X10 Y0 Z-1 F300\n")
    window._start_simulation()
    assert window._latest_simulation_result is not None
    assert window._latest_simulation_result.plane == "XY"
    assert window.gl_canvas._real_path

    window.control_panel.machining_mode_input.setCurrentIndex(1)
    assert window.control_panel.parameters().machining_mode == "车削模式"
    window.editor.set_text("G18\nG0 X20 Z5\nG1 X10 Z-20 F300\n")
    window._start_simulation()
    assert window._latest_simulation_result is not None
    assert window._latest_simulation_result.plane == "XZ"
    assert window.gl_canvas._is_turning is True
    window.close()


def test_canvas_axes_fill_available_space() -> None:
    window = MainWindow()
    window.resize(1400, 900)
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X1 Y0 Z-1 F300\nG1 X1 Y1\n")
    window._start_simulation()

    two_d_pos = window.canvas._axis.get_position()
    three_d_pos = window.gl_canvas._axis.get_position()
    assert two_d_pos.width >= 0.86
    assert two_d_pos.height >= 0.72
    assert three_d_pos.width >= 0.60
    assert three_d_pos.height >= 0.66
    assert window.canvas._axis.get_aspect() == "auto"
    window.close()


def test_2d_canvas_batches_line_drawing_with_collections() -> None:
    window = MainWindow()
    geometry = DxfReadResult(
        lines=[DxfLine(float(index), 0.0, float(index), 10.0, "CUT") for index in range(80)],
        polylines=[DxfPolyline(points=[(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)], is_closed=False, layer="CUT")],
    )

    window.canvas.draw_dxf_geometry(geometry)
    collection_types = [type(collection).__name__ for collection in window.canvas._axis.collections]

    assert collection_types.count("LineCollection") >= 2
    assert len(window.canvas._axis.lines) <= 2
    window.close()


def test_3d_user_camera_survives_animation_redraw() -> None:
    window = MainWindow()
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X20 Y0 Z-1 F300\nG1 X20 Y20\n")
    window._start_simulation()
    window.gl_canvas._axis.view_init(elev=61.0, azim=24.0)
    window.gl_canvas.update_tool_position(10.0, 0.0, -1.0, 0)
    window.gl_canvas._draw_scene()
    assert round(float(window.gl_canvas._axis.elev), 1) == 61.0
    assert round(float(window.gl_canvas._axis.azim), 1) == 24.0
    window.close()


def test_3d_animation_uses_event_driven_redraws() -> None:
    window = MainWindow()
    window.gl_canvas.start_animation()
    assert window.gl_canvas._anim_timer.isActive() is False
    window.close()


def test_canvas_fit_preserves_equal_scale_and_full_visibility() -> None:
    window = MainWindow()
    window.resize(1400, 900)
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X1 Y0 Z-1 F300\nG1 X1 Y1\n")
    window._start_simulation()

    x0, x1 = window.canvas._axis.get_xlim()
    y0, y1 = window.canvas._axis.get_ylim()
    assert x0 <= 0.0 <= x1 and x0 <= 1.0 <= x1
    assert y0 <= 0.0 <= y1 and y0 <= 1.0 <= y1
    bbox = window.canvas._axis.bbox
    x_units_per_px = (x1 - x0) / bbox.width
    y_units_per_px = (y1 - y0) / bbox.height
    assert abs(x_units_per_px - y_units_per_px) / max(x_units_per_px, y_units_per_px) < 0.05
    window.close()


def test_3d_cut_path_tracks_current_tool_position() -> None:
    window = MainWindow()
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X10 Y0 Z-1 F300\nG1 X20 Y0 Z-1 F300\n")
    window._start_simulation()
    window.simulation_runner.stop()
    window.gl_canvas.stop_animation()
    window.gl_canvas.update_tool_position(10.0, 0.0, -1.0, 1)
    cut_path = window.gl_canvas._current_cut_machine_path(cutting_only=False)
    assert cut_path
    assert cut_path[-1] == window.gl_canvas._nearest_path_point((10.0, 0.0, -1.0))
    window.close()


def test_ui_mode_overrides_embedded_plane_codes() -> None:
    window = MainWindow()
    window.control_panel.machining_mode_input.setCurrentIndex(1)
    window.editor.set_text("G17\nG0 X20 Z5\nG1 X10 Z-20 F300\n")
    window._start_simulation()
    assert window._latest_simulation_result is not None
    assert window._latest_simulation_result.plane == "XZ"
    assert window.gl_canvas._is_turning is True

    window.control_panel.machining_mode_input.setCurrentIndex(0)
    window.editor.set_text("G18\nG0 X0 Y0 Z5\nG1 X10 Y10 Z-1 F300\n")
    window._start_simulation()
    assert window._latest_simulation_result is not None
    assert window._latest_simulation_result.plane == "XY"
    assert window.gl_canvas._is_turning is False
    window.close()


def test_milling_shallow_cut_is_counted_as_cutting_path() -> None:
    window = MainWindow()
    window.control_panel.machining_mode_input.setCurrentIndex(0)
    window.editor.set_text("G17\nG0 X0 Y0 Z8\nG1 Z-0.2 F300\nG1 X80 Y0 F600\n")
    window._start_simulation()
    window.simulation_runner.stop()
    window.gl_canvas.stop_animation()
    window.gl_canvas.update_tool_position(40.0, 0.0, -0.2, 1)
    cut_points = window.gl_canvas._current_cut_machine_path(cutting_only=True)
    assert cut_points
    assert any(abs(point[2] + 0.2) < 1e-6 for point in cut_points)
    assert all(point[2] <= 0.0 for point in cut_points)
    window.close()


def test_turning_surface_profile_is_densified_for_continuous_mesh() -> None:
    window = MainWindow()
    window.control_panel.machining_mode_input.setCurrentIndex(1)
    window.editor.set_text("G18\nG0 X52 Z0\nG1 X52 Z-8 F300\nG1 X48 Z-14\nG1 X48 Z-38\nG1 X34 Z-52\nG1 X20 Z-66\nG0 X60 Z4\n")
    window._start_simulation()
    profile_z, profile_r = window.gl_canvas._turning_surface_profile()
    unique_raw_z = len({round(point[2], 4) for point in window.gl_canvas._current_cut_machine_path(cutting_only=True)})
    assert len(profile_z) > unique_raw_z * 2
    assert len(profile_z) == len(profile_r)
    assert all(profile_z[i] <= profile_z[i + 1] for i in range(len(profile_z) - 1))
    window.close()



def test_3d_mesh_defaults_to_translucent_stock_style() -> None:
    window = MainWindow()
    assert 0.35 <= window.gl_canvas._mesh_opacity <= 0.65
    window.close()

def test_3d_swept_mesh_connects_adjacent_sections_with_triangles() -> None:
    window = MainWindow()
    vertices, faces = window.gl_canvas._build_swept_circular_mesh(
        [(0.0, 0.0, 0.0), (0.0, 0.0, 10.0)],
        radius=1.0,
        section_count=3,
        circle_segments=4,
        cap_ends=False,
    )

    assert vertices.shape == (12, 3)
    assert faces.shape == (16, 3)
    assert faces[0].tolist() == [0, 1, 5]
    assert faces[1].tolist() == [0, 5, 4]
    assert faces[6].tolist() == [3, 0, 4]
    assert faces[7].tolist() == [3, 4, 7]
    window.close()

def test_3d_mesh_renderer_does_not_use_trisurf_for_closed_mesh() -> None:
    window = MainWindow()
    vertices, faces = window.gl_canvas._build_swept_circular_mesh(
        [(0.0, 0.0, 0.0), (0.0, 0.0, 10.0)],
        radius=1.0,
        section_count=3,
        circle_segments=8,
        cap_ends=True,
    )

    def fail_trisurf(*_args, **_kwargs):
        raise AssertionError("closed mesh should be rendered from explicit face polygons")

    window.gl_canvas._axis.plot_trisurf = fail_trisurf
    window.gl_canvas._plot_triangle_mesh(
        vertices,
        faces,
        color="#22c55e",
        opacity=1.0,
        show_edges=False,
    )

    assert any(type(collection).__name__ == "Poly3DCollection" for collection in window.gl_canvas._axis.collections)
    window.close()

def test_parameter_forms_wrap_rows_to_avoid_narrow_panel_overlap() -> None:
    window = MainWindow()
    assert window.control_panel.cutter_compensation_input.property("formRowWrap") is True
    assert window.control_panel.cutter_compensation_input.minimumWidth() <= 150
    window.close()

def test_timeline_speed_slider_updates_runner_speed() -> None:
    window = MainWindow()
    slider = window.timeline_panel.speed_slider
    label = window.timeline_panel.speed_label
    assert slider.minimum() <= 10 <= slider.maximum()
    slider.setValue(25)
    assert abs(window.simulation_runner._speed_multiplier - 2.5) < 1e-9
    assert "2.5" in label.text()
    slider.setValue(5)
    assert abs(window.simulation_runner._speed_multiplier - 0.5) < 1e-9
    assert "0.5" in label.text()
    window.close()


def test_generate_gcode_does_not_start_simulation() -> None:
    window = MainWindow()
    window.current_dxf_result = DxfReadResult(
        polylines=[DxfPolyline(points=[(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)], is_closed=True)]
    )
    window._generate_gcode()
    assert window.editor.text().strip()
    assert window._latest_simulation_result is None
    assert window.simulation_runner.is_playing() is False
    assert window.gl_canvas._real_path == []
    window.close()


def test_speed_title_is_readable_text() -> None:
    window = MainWindow()
    assert window.timeline_panel.speed_title.text() == "\u64ad\u653e\u901f\u5ea6"
    assert "?" not in window.timeline_panel.speed_title.text()
    window.close()


def test_3d_draw_is_deferred_while_user_is_interacting() -> None:
    window = MainWindow()
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X20 Y0 Z-1 F300\n")
    window._start_simulation()
    axis_id = id(window.gl_canvas._axis)
    window.gl_canvas._user_interacting = True
    window.gl_canvas._draw_scene()
    assert id(window.gl_canvas._axis) == axis_id
    assert window.gl_canvas._draw_pending_after_interaction is True
    window.close()


def test_turning_surface_starts_as_bar_stock_and_finishes_as_profile() -> None:
    window = MainWindow()
    window.control_panel.machining_mode_input.setCurrentIndex(1)
    window.editor.set_text("G18\nG0 X52 Z0\nG1 X52 Z-8 F300\nG1 X40 Z-30\nG1 X20 Z-60\n")
    window._start_simulation()
    window.simulation_runner.stop()
    window.gl_canvas.stop_animation()

    window.gl_canvas.update_cut_progress(0.0)
    _z0, r0 = window.gl_canvas._turning_surface_profile()
    assert max(r0) - min(r0) < 1e-6

    window.gl_canvas.update_cut_progress(1.0)
    _z1, r1 = window.gl_canvas._turning_surface_profile()
    assert max(r1) - min(r1) > 10.0
    assert min(r1) < min(r0)
    window.close()


def test_2d_title_and_axis_labels_have_safe_layout() -> None:
    window = MainWindow()
    window.resize(1400, 900)
    window.control_panel.machining_mode_input.setCurrentIndex(0)
    window.editor.set_text("G17\nG0 X0 Y0 Z5\nG1 X10 Y5 Z-1 F300\n")
    window._start_simulation()
    pos = window.canvas._axis.get_position()
    assert pos.y1 <= 0.91
    assert pos.y0 >= 0.09
    assert window.canvas._axis.get_xlabel() == "X / mm"
    assert window.canvas._axis.get_ylabel() == "Y / mm"

    window.control_panel.machining_mode_input.setCurrentIndex(1)
    window.editor.set_text("G18\nG0 X20 Z5\nG1 X10 Z-20 F300\n")
    window._start_simulation()
    assert window.canvas._axis.get_xlabel() == "Z / mm"
    assert window.canvas._axis.get_ylabel() == "X / mm"
    window.close()


def test_3d_home_axes_keep_label_margins() -> None:
    window = MainWindow()
    window.gl_canvas.reset_view()
    window.gl_canvas._draw_scene()
    pos = window.gl_canvas._axis.get_position()
    assert pos.x0 >= 0.03
    assert pos.y0 >= 0.03
    assert pos.x1 <= 0.97
    assert pos.y1 <= 0.95
    window.close()


def test_rendered_axis_labels_stay_inside_canvas() -> None:
    window = MainWindow()
    window.resize(1500, 900)
    window.control_panel.machining_mode_input.setCurrentIndex(1)
    window.editor.set_text("G18\nG0 X20 Z5\nG1 X10 Z-20 F300\n")
    window._start_simulation()
    window.simulation_runner.stop()
    window.gl_canvas.stop_animation()

    window.canvas._canvas.draw()
    renderer = window.canvas._canvas.get_renderer()
    fig_bbox = window.canvas._figure.bbox
    for artist in (window.canvas._axis.xaxis.label, window.canvas._axis.yaxis.label, window.canvas._axis.title):
        bbox = artist.get_window_extent(renderer)
        assert bbox.x0 >= 0.0
        assert bbox.y0 >= 0.0
        assert bbox.x1 <= fig_bbox.width
        assert bbox.y1 <= fig_bbox.height

    window.gl_canvas.reset_view()
    window.gl_canvas._draw_scene()
    window.gl_canvas._canvas.draw()
    renderer3d = window.gl_canvas._canvas.get_renderer()
    fig_bbox3d = window.gl_canvas._figure.bbox
    for artist in (window.gl_canvas._axis.xaxis.label, window.gl_canvas._axis.yaxis.label, window.gl_canvas._axis.zaxis.label, window.gl_canvas._axis.title):
        bbox = artist.get_window_extent(renderer3d)
        assert bbox.x0 >= 0.0
        assert bbox.y0 >= 0.0
        assert bbox.x1 <= fig_bbox3d.width
        assert bbox.y1 <= fig_bbox3d.height
    window.close()


def main() -> None:
    tests = [
        test_incremental_coordinates,
        test_r_arc_and_radius_warning,
        test_r_arc_does_not_warn_about_missing_ijk,
        test_arc_missing_center_or_radius_warning_is_readable,
        test_arc_missing_endpoint_warning_is_readable,
        test_ijk_full_circle_without_endpoint_is_valid,
        test_turning_arc_i_uses_radius_coordinate,
        test_runner_uses_segment_positions,
        test_empty_runner_play_does_not_enter_playing_state,
        test_clear_then_play_keeps_runner_idle,
        test_start_simulation_with_no_motion_clears_old_runner,
        test_start_simulation_with_empty_editor_clears_old_runner,
        test_simulation_summary_uses_runner_duration,
        test_build_script_uses_portable_python_launcher,
        test_read_text_with_fallback_handles_chinese_windows_files,
        test_dxf_reader_preserves_layers_and_filters_geometry,
        test_dxf_reader_expands_insert_and_spline,
        test_cam_generation_respects_selected_layer,
        test_milling_cutter_compensation_offsets_closed_contour,
        test_main_window_populates_layer_filter_from_dxf,
        test_project_tree_and_operation_table_use_real_data,
        test_demo_image_candidates_stay_under_assets,
        test_main_window_milling_and_turning_modes,
        test_canvas_axes_fill_available_space,
        test_2d_canvas_batches_line_drawing_with_collections,
        test_3d_user_camera_survives_animation_redraw,
        test_3d_animation_uses_event_driven_redraws,
        test_canvas_fit_preserves_equal_scale_and_full_visibility,
        test_3d_cut_path_tracks_current_tool_position,
        test_ui_mode_overrides_embedded_plane_codes,
        test_milling_shallow_cut_is_counted_as_cutting_path,
        test_turning_surface_profile_is_densified_for_continuous_mesh,
        test_3d_mesh_defaults_to_translucent_stock_style,
        test_3d_swept_mesh_connects_adjacent_sections_with_triangles,
        test_3d_mesh_renderer_does_not_use_trisurf_for_closed_mesh,
        test_parameter_forms_wrap_rows_to_avoid_narrow_panel_overlap,
        test_timeline_speed_slider_updates_runner_speed,
        test_generate_gcode_does_not_start_simulation,
        test_speed_title_is_readable_text,
        test_3d_draw_is_deferred_while_user_is_interacting,
        test_turning_surface_starts_as_bar_stock_and_finishes_as_profile,
        test_2d_title_and_axis_labels_have_safe_layout,
        test_3d_home_axes_keep_label_margins,
        test_rendered_axis_labels_stay_inside_canvas,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")


if __name__ == "__main__":
    main()
