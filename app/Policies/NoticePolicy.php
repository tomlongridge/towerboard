<?php

namespace App\Policies;

use App\User;
use App\Notice;
use App\Board;
use Illuminate\Auth\Access\HandlesAuthorization;

class NoticePolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can view the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function view(?User $user, Notice $notice)
    {
        return true;
    }

    /**
     * Determine whether the user can create notices.
     *
     * @param  \App\User  $user
     * @return mixed
     */
    public function create(User $user)
    {
        return $user != null;
    }

    /**
     * Determine whether the user can update the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function update(User $user, Notice $notice)
    {
        return $user->id == $notice->board->owner->id;
    }

    /**
     * Determine whether the user can delete the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function delete(User $user, Notice $notice)
    {
        return $user->id == $notice->board->owner->id;
    }

    /**
     * Determine whether the user can restore the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function restore(User $user, Notice $notice)
    {
        return $user->id == $notice->board->owner->id;
    }

    /**
     * Determine whether the user can permanently delete the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function forceDelete(User $user, Notice $notice)
    {
        return false;
    }
}