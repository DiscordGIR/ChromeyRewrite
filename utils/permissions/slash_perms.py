from discord.commands.permissions import Permission

from typing import List
from utils.permissions.permissions import permissions

class SlashPerms:
    ####################
    # Staff Roles
    ####################
    
    def nerds_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(1)

    def mod_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(2)

    def admin_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(3)

    ####################
    # Other
    ####################

    def guild_owner_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(4)

    def bot_owner_and_up(self) -> List[Permission]:
        return permissions.calculate_permissions(5)

slash_perms = SlashPerms()
