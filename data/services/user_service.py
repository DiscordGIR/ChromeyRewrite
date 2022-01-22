from typing import Counter
from data.model.case import Case
from data.model.cases import Cases
from data.model.user import User

class UserService:
    def get_user(self, id: int) -> User:
        """Look up the User document of a user, whose ID is given by `id`.
        If the user doesn't have a User document in the database, first create that.

        Parameters
        ----------
        id : int
            The ID of the user we want to look up

        Returns
        -------
        User
            The User document we found from the database.
        """

        user = User.objects(_id=id).first()
        # first we ensure this user has a User document in the database before continuing
        if not user:
            user = User()
            user._id = id
            user.save()
        return user

    def get_cases(self, id: int) -> Cases:
        """Return the Document representing the cases of a user, whose ID is given by `id`
        If the user doesn't have a Cases document in the database, first create that.

        Parameters
        ----------
        id : int
            The user whose cases we want to look up.

        Returns
        -------
        Cases
            [description]
        """

        cases = Cases.objects(_id=id).first()
        # first we ensure this user has a Cases document in the database before continuing
        if cases is None:
            cases = Cases()
            cases._id = id
            cases.save()
        return cases
    
    def add_case(self, _id: int, case: Case) -> None:
        """Cases holds all the cases for a particular user with id `_id` as an
        EmbeddedDocumentListField. This function appends a given case object to
        this list. If this user doesn't have any previous cases, we first add
        a new Cases document to the database.

        Parameters
        ----------
        _id : int
            ID of the user who we want to add the case to.
        case : Case
            The case we want to add to the user.
        """

        # ensure this user has a cases document before we try to append the new case
        self.get_cases(_id)
        Cases.objects(_id=_id).update_one(push__cases=case)

    def rundown(self, id: int) -> list:
        """Return the 3 most recent cases of a user, whose ID is given by `id`
        If the user doesn't have a Cases document in the database, first create that.

        Parameters
        ----------
        id : int
            The user whose cases we want to look up.

        Returns
        -------
        Cases
            [description]
        """

        cases = Cases.objects(_id=id).first()
        # first we ensure this user has a Cases document in the database before continuing
        if cases is None:
            cases = Cases()
            cases._id = id
            cases.save()
            return []

        cases = cases.cases
        cases = filter(lambda x: x._type != "UNMUTE", cases)
        cases = sorted(cases, key=lambda i: i['date'])
        cases.reverse()
        return cases[0:3]

    def retrieve_birthdays(self, date):
        return User.objects(birthday=date)
    
    def transfer_profile(self, oldmember, newmember):
        u = self.get_user(oldmember)
        u._id = newmember
        u.save()
        
        u2 = self.get_user(oldmember)
        u2.save()
        
        cases = self.get_cases(oldmember)
        cases._id = newmember
        cases.save()
        
        cases2 = self.get_cases(oldmember)
        cases2.cases = []
        cases2.save()
        
        return u, len(cases.cases)
    
    def fetch_raids(self):
        values = {}
        values["Join spam"] = Cases.objects(cases__reason__contains="Join spam detected").count()
        values["Join spam over time"] = Cases.objects(cases__reason__contains="Join spam over time detected").count()
        values["Raid phrase"] = Cases.objects(cases__reason__contains="Raid phrase detected").count()
        values["Ping spam"] = Cases.objects(cases__reason__contains="Ping spam").count()
        values["Message spam"] = Cases.objects(cases__reason__contains="Message spam").count()
        
        return values

    def fetch_cases_by_mod(self, _id):
        values = {}
        cases = Cases.objects(cases__mod_id=str(_id))
        values["total"] = 0
        cases = list(cases.all())
        final_cases = []
        for case in cases:
            for c in case.cases:
                final_cases.append(c)
                values["total"] += 1
 
        def get_case_reason(reason):
            string = reason.lower()
            return ''.join(e for e in string if e.isalnum() or e == " ").strip()
        case_reasons = [get_case_reason(case.reason) for case in final_cases if get_case_reason(case.reason) != "temporary mute expired"]
        values["counts"] = sorted(Counter(case_reasons).items(), key=lambda item: item[1])
        values["counts"].reverse()
        return values

    def set_sticky_roles(self, _id: int, roles) -> None:
        self.get_user(_id)
        User.objects(_id=_id).update_one(set__sticky_roles=roles)

user_service = UserService()