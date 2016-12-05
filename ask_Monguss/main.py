#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from user import User
from course import Course
from faq import FAQ
from question import Question
from timestamp import Timestamp
from reply import Reply
import time
import datetime
from google.appengine.ext import ndb

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class MainHandler(webapp2.RequestHandler):
    def get(self):
        #check if generic janedoe account exists, if not, populate info for starting point
        student = User.query(User.ePantherID == "janedoe").fetch()
        if len(student) == 0:
            #create new course
            course_key = Course(name="CS361").put()

            #create new users
            janedoe_key = User(ePantherID="janedoe", password="janedoe", isInstructor=0).put()
            jrock_key = User(ePantherID="jrock", password="jrock", isInstructor=1).put()

            #pull course info from key
            course = course_key.get()

            #update course instructors by appending an instructor
            course.instructors.append(jrock_key)
            course.put()

            # update course students by appending a student
            course.students.append(janedoe_key)
            course.put()

            #pull instructor from key and add a course
            instructor = jrock_key.get()
            instructor.courses.append(course_key)
            instructor.put()

            # pull student from key and add a course
            student = janedoe_key.get()
            student.courses.append(course_key)
            student.put()

        template = JINJA_ENVIRONMENT.get_template('HTML/Login.html')
        self.response.write(template.render())


class LoginHandler(webapp2.RequestHandler):
    postedUsername = ""
    postedPassword = ""
    match = -1

    def checkForMatch(self, username, password):
        # pull all students and check
        students = User.query(User.ePantherID == username and User.isInstructor == 0).fetch()
        for s in students:
            if s.password == password:
                return 0

        # pull all instructors and check
        instructors = User.query(User.ePantherID == username and User.isInstructor == 1).fetch()
        for i in instructors:
            if i.password == password:
                return 1

        # check if administrator
        if username == "ADMIN" and password == "ADMIN":
            return 2
        return -1

    def post(self):
        self.postedUsername = self.request.get('ePantherID')
        self.postedPassword = self.request.get('password')

        self.match = self.checkForMatch(self.postedUsername, self.postedPassword)

        if self.match == -1:
            values = {
                'credentials': self.match
            }

            template = JINJA_ENVIRONMENT.get_template('HTML/Login.html')
            self.response.write(template.render(values))
            return

        elif self.match == 0:
            self.response.set_cookie('name', self.postedUsername, path='/')
            self.redirect('/student')
            return

        elif self.match == 1:
            self.response.set_cookie('name', self.postedUsername, path='/')
            self.redirect('/instructor')
            return

        elif self.match == 2:
            self.response.set_cookie('name', self.postedUsername, path='/')
            self.redirect('/ADMIN')
            return


class LogoutHandler(webapp2.RequestHandler):
    def get(self):
        name = self.request.cookies.get('name')
        self.response.delete_cookie('name')
        value = {
            'username': name
        }

        template = JINJA_ENVIRONMENT.get_template('HTML/Logout.html')
        self.response.write(template.render(value))


class ChangePasswordHandler(webapp2.RequestHandler):
    def get(self):
        name = self.request.cookies.get('name')
        all_users = User.query(User.ePantherID == name).fetch()

        if len(all_users) != 0:
            value = {
                'username': name,
                'incorrectPassword': 0
            }

            template = JINJA_ENVIRONMENT.get_template('HTML/Change Password.html')
            self.response.write(template.render(value))

        else:
            self.redirect('/')

    def post(self):
        name = self.request.cookies.get('name')
        all_users = User.query(User.ePantherID == name).fetch()

        if len(all_users) != 0:
            curUser = all_users[0]

            curPassword = self.request.get('curPassword')
            newPassword = self.request.get('newPassword')

            # check if passwords match, then set new password
            if curPassword == curUser.password:
                curUser.password = newPassword
                curUser.put()

                values = {
                    "isInstructor": curUser.isInstructor
                }

                template = JINJA_ENVIRONMENT.get_template('HTML/Change Password Successful.html')
                self.response.write(template.render(values))
                return

            # if current password doesn't match, render error
            else:
                values = {
                    'username': curUser.ePantherID,
                    'incorrectPassword': 1
                }

                template = JINJA_ENVIRONMENT.get_template('HTML/Change Password.html')
                self.response.write(template.render(values))
                return

        else:
            self.redirect('/')


class StudentLandingPageHandler(webapp2.RequestHandler):
    def get(self):
        #check for correct cookie
        name = self.request.cookies.get("name")
        students = User.query(User.ePantherID == name, User.isInstructor == 0).fetch()

        #if cookie is correct, render page
        if len(students) != 0:
            curStudent = students[0]
            values = {
                "username": curStudent.ePantherID
            }
            template = JINJA_ENVIRONMENT.get_template('HTML/Student Home.html')
            self.response.write(template.render(values))

        #else redirect to login page
        else:
            self.redirect('/')


class StudentAskHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        students = User.query(User.ePantherID == name, User.isInstructor == 0).fetch()

        # if cookie is correct, render page
        if len(students) != 0:
            curStudent = students[0]

            values = {
                'username': curStudent.ePantherID,
                'course': curStudent.courses
                # 'instructor': curStudent.instructor
            }

            template = JINJA_ENVIRONMENT.get_template('HTML/Student Question Submission Form.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')

    def post(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        students = User.query(User.ePantherID == name, User.isInstructor == 0).fetch()

        # if cookie is correct, render page
        if len(students) != 0:
            q = Question(str(self.request.get('textbox')))
            q.student = self.request.get(name)
            q.instructor = self.request.get('instructor')
            q.timestamp = datetime.datetime.now().strftime('%m-%d-%Y')

            # put question to datastore
            q_key = q.put()

            # add question to student's list
            name.questions.append(q_key)
            name.put()

            # add question to course list
            course = Course.query(Course.name == self.request.get('course'))[0]
            course.questions.append(q_key)

            self.redirect('/student')

        # else redirect to login page
        else:
            self.redirect('/')


class StudentFAQHandler(webapp2.RequestHandler):
   def get(self):
        #check for correct cookie
        name = self.request.cookies.get("name")
        students = User.query(User.ePantherID == name, User.isInstructor == 0).fetch()

        #if cookie is correct, render page
        if len(students) != 0:
            curStudent = students[0]
            values = {
                "username": curStudent.ePantherID,
                "isInstructor": 0
            }
            template = JINJA_ENVIRONMENT.get_template('HTML/Student FAQ.html')
            self.response.write(template.render(values))

        #else redirect to login page
        else:
            self.redirect('/')


class StudentViewAllQuestionsHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        students = User.query(User.ePantherID == name, User.isInstructor == 0).fetch()

        # if cookie is correct, render page
        if len(students) != 0:
            curStudent = students[0]
            values = {
                "username": curStudent.ePantherID,
            }
            template = JINJA_ENVIRONMENT.get_template('HTML/Student View All Answers.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')


class InstructorLandingPageHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        instructors = User.query(User.ePantherID == name, User.isInstructor == 1).fetch()

        # if cookie is correct, render page
        if len(instructors) != 0:
            curInstructor = instructors[0]
            values = {
                "username": curInstructor.ePantherID,
            }
            template = JINJA_ENVIRONMENT.get_template('HTML/Instructor Home.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')


class InstructorViewAllQuestionsHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        instructors = User.query(User.ePantherID == name, User.isInstructor == 1).fetch()

        # if cookie is correct, render page
        if len(instructors) != 0:
            curInstructor = instructors[0]

            option = self.request.get('option')
            # check if a dropdown has been selected, if not, set isChosen to 0 and don't render table
            if option == "":
                values = {
                    "username": curInstructor.ePantherID,
                    "courses": curInstructor.courses,
                    "isChosen": 0
                }
            else:
                selected_course_list = Course.Query(name=option).fetch()
                selected_course = selected_course_list[0]
                values = {
                    "username": curInstructor.ePantherID,
                    "courses": curInstructor.courses,
                    "isChosen": 0,
                    "selected_course": selected_course
                }
            template = JINJA_ENVIRONMENT.get_template('HTML/Instructor View Questions.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')


class InstructorFaqHandler(webapp2.RequestHandler):
    def get(self):
        name = self.request.cookies.get("name")
        instructors = User.query(User.ePantherID == name, User.isInstructor == 1).fetch()

        # if cookie is correct, render page
        if len(instructors) != 0:
            curInstructor = instructors[0]
            faqs = list(FAQ.query().order(FAQ.ts))
            values = {
                "username": curInstructor.ePantherID,
                "faqs": faqs
            }
            faqs = list(FAQ.query().order(FAQ.ts))

            template = JINJA_ENVIRONMENT.get_template('HTML/Instructor FAQ.html')
            self.response.write(template.render(values))


        # else redirect to login page
        else:
            self.redirect('/')


class InstructorFaqAddHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        instructors = User.query(User.ePantherID == name, User.isInstructor == 1).fetch()

        # if cookie is correct, render page
        if len(instructors) != 0:
            curInstructor = instructors[0]
            values = {
                "username": curInstructor.ePantherID,
            }
            template = JINJA_ENVIRONMENT.get_template('HTML/Instructor FAQ Add.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')

    def post(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        instructors = User.query(User.ePantherID == name, User.isInstructor == 1).fetch()

        # if cookie is correct, render page
        if len(instructors) != 0:
            question = self.request.get('question')

            answer = self.request.get('answer')
            faq = FAQ(question=question, answer=answer)
            faq.put()
            self.response.write('<meta http-equiv="refresh" content="0.5;url=/instructor/faq">')

        # else redirect to login page
        else:
            self.redirect('/')


class InstructorDeleteHandler(webapp2.RequestHandler):
    def get(self):
        pass

    def post(self):
        pass


class ADMINHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        # if cookie is correct, render page
        if name == "ADMIN":
            numberOfStudents = User.query(User.isInstructor == 0).count()
            numberOfInstructors = User.query(User.isInstructor == 1).count()
            numberOfCourses = Course.query().count()
            studentInstructorRatio = numberOfStudents / numberOfInstructors

            values = {
                "username": name,
                "numberOfStudents": numberOfStudents,
                "numberOfInstructors": numberOfInstructors,
                "numberOfCourses": numberOfCourses,
                "studentInstructorRatio": studentInstructorRatio
            }

            template = JINJA_ENVIRONMENT.get_template('HTML/ADMIN.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')

    def post(self):
        pass


class ADMINAccountCreationHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        if name == "ADMIN":
            values = {
                "username": "ADMINISTRATOR"
            }
            template = JINJA_ENVIRONMENT.get_template('HTML/Account Creation.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')

    def post(self):
        # check for correct cookie
        name = self.request.cookies.get("name")

        if name == "ADMIN":
            username = self.request.get('ePantherID')
            password = self.request.get('password')
            credential = self.request.get('credential')

            if credential == "instructor":
                list = User.query(User.ePantherID == username).fetch()
                if len(list) == 0:
                    newUser = User(ePantherID=username, password=password, isInstructor=1)
                    newUser.put()
                    values = {
                        'username': username,
                        'password': password,
                        'isInstructor': 1
                    }
                    # Refresh and write error message
                    template = JINJA_ENVIRONMENT.get_template('HTML/Account Creation Successful.html')
                    self.response.write(template.render(values))
                    return

                else:
                    userAlreadyExists = 1
                    values = {
                        'userAlreadyExists': userAlreadyExists,
                        'username': username
                    }
                    #Refresh and write error message
                    template = JINJA_ENVIRONMENT.get_template('HTML/Account Creation.html')
                    self.response.write(template.render(values))
                    return

            if credential == "student":
                list = User.query(User.ePantherID == username).fetch()
                if len(list) == 0:
                    newUser = User(ePantherID=username, password=password, isInstructor=0)
                    newUser.put()
                    values = {
                        'username': username,
                        'password': password,
                        'isInstructor': 0
                    }
                    # Refresh and write error message
                    template = JINJA_ENVIRONMENT.get_template('HTML/Account Creation Successful.html')
                    self.response.write(template.render(values))
                    return

                else:
                    userAlreadyExists = 1
                    values = {
                        'userAlreadyExists': userAlreadyExists,
                        'username': username
                    }
                    # Refresh and write error message
                    template = JINJA_ENVIRONMENT.get_template('HTML/Account Creation.html')
                    self.response.write(template.render(values))
                    return

        # else redirect to login page
        else:
            self.redirect('/')


class ADMINCourseCreationHandler(webapp2.RequestHandler):
    def get(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        if name == "ADMIN":
            all_instructors = User.query(User.isInstructor == 1).fetch()
            all_students = User.query(User.isInstructor == 0).fetch()

            values = {
                "username": "ADMINISTRATOR",
                "all_instructors": all_instructors,
                "all_students": all_students
            }

            template = JINJA_ENVIRONMENT.get_template('HTML/Course Creation.html')
            self.response.write(template.render(values))

        # else redirect to login page
        else:
            self.redirect('/')

    def post(self):
        # check for correct cookie
        name = self.request.cookies.get("name")
        if name == "ADMIN":
            # store form data
            course_ID = self.request.get('courseID')
            selected_instructors_list = self.request.get_all('instructors')
            selected_students_list = self.request.get_all('students')

            # create new course and retain key
            course_key = Course(name=course_ID).put()
            course = course_key.get()

            # iterate over check boxes to add instructors to courses
            for i in selected_instructors_list:
                instructor = User.query(User.ePantherID == i).fetch()[0]

                # add course key to instructor and put back
                instructor.courses.append(course_key)
                instructor.put()

                # add instructor key to course and put back
                course.instructors.append(instructor.key)
                course.put()

            # iterate over check boxes to add students to courses
            for s in selected_students_list:
                student = User.query(User.ePantherID == s).fetch()[0]

                # add course key to student and put back
                student.courses.append(course_key)
                student.put()

                # add student key to course and put back
                course.students.append(student.key)
                course.put()

            values = {
                "courseID": course_ID,
                "addedStudents": selected_students_list,
                "addedInstructors": selected_instructors_list
            }

            template = JINJA_ENVIRONMENT.get_template('HTML/Course Creation Successful.html')
            self.response.write(template.render(values))


        # else redirect to login page
        else:
            self.redirect('/')


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/change_password',ChangePasswordHandler),
    ('/student', StudentLandingPageHandler),
    ('/student/ask', StudentAskHandler),
    ('/student/faq', StudentFAQHandler),
    ('/student/view_all', StudentViewAllQuestionsHandler),
    ('/instructor', InstructorLandingPageHandler),
    ('/instructor/view_all', InstructorViewAllQuestionsHandler),
    ('/instructor/faq', InstructorFaqHandler),
    ('/instructor/faq/faq_add', InstructorFaqAddHandler),
    ('/instructor/faq/faq_delete', InstructorDeleteHandler),
    ('/ADMIN', ADMINHandler),
    ('/ADMIN/create_user', ADMINAccountCreationHandler),
    ('/ADMIN/create_course', ADMINCourseCreationHandler)
], debug=True)
