# =============================================================================
# RichDashboard: Live Table + Progress Bar + ETA (for CLI dashboard)
# =============================================================================

try:
    import threading
    import time
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.live import Live
    from rich.text import Text

    class RichDashboard:
        def __init__(self, total_steps):
            self.console = Console()
            self.headers = [
                "Host", "Sheet", "Test Name", "Method", "Result", "Duration (s)"
            ]
            self.all_results = []
            self.total_steps = total_steps
            self.completed_steps = 0
            self.start_time = time.time()
            self.progress = Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TextColumn("[cyan]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                expand=True,
            )
            self.progress_task = self.progress.add_task("Progress", total=total_steps)
            self.live = None
            self.lock = threading.Lock()

        def _create_table(self):
            table = Table(show_header=True, header_style="bold magenta")
            for h in self.headers:
                table.add_column(h)
            for r in self.all_results:
                host = getattr(r, "host", "")
                sheet = getattr(r, "sheet", "")
                test_name = getattr(r, "test_name", "")
                method = getattr(r, "method", "") if hasattr(r, "method") else ""
                duration = f"{getattr(r, 'duration', 0.0):.2f}"
                if hasattr(r, "result") and getattr(r, "result", "") == "DRY-RUN":
                    result = Text("DRY-RUN", style="yellow")
                elif getattr(r, "passed", False):
                    result = Text("PASS", style="green")
                else:
                    result = Text("FAIL", style="red")
                table.add_row(host, sheet, test_name, method, result, duration)
            return table

        def start(self):
            self.live = Live(self._render_dashboard(), refresh_per_second=10, console=self.console)
            self.live.__enter__()

        def _render_dashboard(self):
            table = self._create_table()
            return self.progress.get_renderable(), table

        def add_result(self, test_result):
            with self.lock:
                self.all_results.append(test_result)
                self.completed_steps += 1
                self.progress.update(self.progress_task, completed=self.completed_steps)
                self.live.update(self._render_dashboard())

        def stop(self):
            if self.live:
                self.live.__exit__(None, None, None)
            self.progress.stop()

        def print_final_summary(self):
            passed = sum(1 for r in self.all_results if getattr(r, "passed", False))
            failed = len(self.all_results) - passed
            self.console.print(f"\n[bold]FINAL SUMMARY:[/bold] [green]{passed} PASSED[/green] | [red]{failed} FAILED[/red] | {len(self.all_results)} TOTAL")

        def start(self):
            self.live = Live(self._render_dashboard(), refresh_per_second=10, console=self.console)
            self.live.__enter__()

        def _render_dashboard(self):
            table = self._create_table()
            return self.progress.get_renderable(), table

        def add_result(self, test_result):
            with self.lock:
                self.all_results.append(test_result)
                self.completed_steps += 1
                self.progress.update(self.progress_task, completed=self.completed_steps)
                self.live.update(self._render_dashboard())

        def stop(self):
            if self.live:
                self.live.__exit__(None, None, None)
            self.progress.stop()

        def print_final_summary(self):
            passed = sum(1 for r in self.all_results if getattr(r, "passed", False))
            failed = len(self.all_results) - passed
            self.console.print(f"\n[bold]FINAL SUMMARY:[/bold] [green]{passed} PASSED[/green] | [red]{failed} FAILED[/red] | {len(self.all_results)} TOTAL")

except ImportError:
    RichDashboard = None
