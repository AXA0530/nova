import os
import json
import time
from typing import List, Dict, Optional

class Student:
    def __init__(self, sid: str, name: str):
        self.sid = sid
        self.name = name
        self.scores: Dict[str, float] = {}

    def add_score(self, subject: str, score: float):
        if not (0 <= score <= 100):
            raise ValueError("成绩必须在0‑100区间内")
        self.scores[subject] = round(score, 1)

    def del_subject(self, subject: str):
        if subject not in self.scores:
            raise KeyError("不存在该科目的成绩")
        del self.scores[subject]

    def get_average(self) -> float:
        if len(self.scores) == 0:
            return 0.0
        total = sum(self.scores.values())
        return round(total / len(self.scores), 2)

    def get_total(self) -> float:
        return round(sum(self.scores.values()), 2)

    def to_dict(self) -> dict:
        return {
            "sid": self.sid,
            "name": self.name,
            "scores": self.scores
        }

    @staticmethod
    def from_dict(data: dict):
        s = Student(data["sid"], data["name"])
        s.scores = data["scores"]
        return s


class ScoreSystem:
    def __init__(self):
        self.student_list: List[Student] = []
        self.data_file = "student_data.json"
        self.load_data()

    def add_student(self, sid: str, name: str) -> bool:
        for stu in self.student_list:
            if stu.sid == sid:
                print("⚠该学号已经存在！")
                return False
        new_stu = Student(sid, name)
        self.student_list.append(new_stu)
        return True

    def search_by_id(self, sid: str) -> Optional[Student]:
        for stu in self.student_list:
            if stu.sid == sid:
                return stu
        return None

    def delete_student(self, sid: str) -> bool:
        target = self.search_by_id(sid)
        if target is None:
            return False
        self.student_list.remove(target)
        return True

    def sort_by_total(self):
        self.student_list.sort(key=lambda x: x.get_total(), reverse=True)

    def save_data(self):
        save_data = [s.to_dict() for s in self.student_list]
        with open(self.data_file, "w", encoding="utf‑8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

    def load_data(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf‑8") as f:
                raw = json.load(f)
            self.student_list = [Student.from_dict(d) for d in raw]
        except Exception:
            print("数据文件损坏，已重置空白系统")
            self.student_list = []


def print_menu():
    print("\n=======学生成绩管理系统=======")
    print("【1】新增学生")
    print("【2】录入/修改科目成绩")
    print("【3】删除一门科目成绩")
    print("【4】按学号查询学生信息")
    print("【5】删除学生档案")
    print("【6】总分降序排序全体学生")
    print("【7】展示全部学生简表")
    print("【8】保存数据并退出程序")
    print("==============================")


def main():
    app = ScoreSystem()
    print("欢迎使用学生成绩综合管理系统")
    while True:
        print_menu()
        opt = input("请输入功能编号：").strip()
        if opt == "1":
            sid = input("输入学生学号：").strip()
            name = input("输入学生姓名：").strip()
            if app.add_student(sid, name):
                print(f"✅学生【{name}】添加成功")
        elif opt == "2":
            sid = input("输入目标学号：").strip()
            stu = app.search_by_id(sid)
            if not stu:
                print("❌查无此学生")
                continue
            sub = input("输入科目名称：").strip()
            try:
                sc = float(input("输入科目成绩："))
                stu.add_score(sub, sc)
                print("✅成绩录入完成")
            except ValueError as e:
                print(f"❌失败：{e}")
        elif opt == "3":
            sid = input("输入目标学号：").strip()
            stu = app.search_by_id(sid)
            if not stu:
                print("❌查无此学生")
                continue
            sub = input("要删除的科目名：").strip()
            try:
                stu.del_subject(sub)
                print("✅科目成绩已删除")
            except KeyError as e:
                print(f"❌失败：{e}")
        elif opt == "4":
            sid = input("输入查询学号：").strip()
            stu = app.search_by_id(sid)
            if not stu:
                print("❌未找到该学生")
                continue
            print(f"\n学号:{stu.sid}｜姓名:{stu.name}")
            print("各科成绩：", stu.scores)
            print(f"总分：{stu.get_total()}｜平均分：{stu.get_average()}")
        elif opt == "5":
            sid = input("要删除学生的学号：").strip()
            confirm = input("确认删除?(y/n):").lower()
            if confirm == "y":
                if app.delete_student(sid):
                    print("✅学生档案已删除")
                else:
                    print("❌未找到该学号")
        elif opt == "6":
            app.sort_by_total()
            print("✅已按照总分从高到低排序")
        elif opt == "7":
            if len(app.student_list) == 0:
                print("暂无学生数据")
                continue
            print("\n学号\t姓名\t总分\t平均分")
            for s in app.student_list:
                print(f"{s.sid}\t{s.name}\t{s.get_total()}\t{s.get_average()}")
        elif opt == "8":
            app.save_data()
            print("💾所有数据已保存，程序即将退出")
            time.sleep(1)
            break
        else:
            print("❗输入无效，请输入1‑8之间数字")


if __name__ == "__main__":
    main()
