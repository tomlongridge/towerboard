<?php

namespace App\Policies;

use App\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\Board;
use App\Notice;

class NoticeMessagePolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can view the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function view(?User $user, Board $board, Notice $notice)
    {
        return true;
    }

    /**
     * Determine whether the user can create notices.
     *
     * @param  \App\User  $user
     * @return mixed
     */
    public function create(User $user, Board $board, Notice $notice)
    {
        if ($user == null) {
            return false;
        }
        return ($notice->createdBy->id == $user->id) || $notice->board->isAdmin($user);
    }

    /**
     * Determine whether the user can update the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function update(User $user, Board $board, Notice $notice)
    {
        return $this->update($user, $board, $notice);
    }

    /**
     * Determine whether the user can delete the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function delete(User $user, Board $board, Notice $notice)
    {
        return $this->update($user, $board, $notice);
    }

    /**
     * Determine whether the user can restore the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function restore(User $user, Board $board, Notice $notice)
    {
        return $this->update($user, $board, $notice);
    }

    /**
     * Determine whether the user can permanently delete the notice.
     *
     * @param  \App\User  $user
     * @param  \App\Notice  $notice
     * @return mixed
     */
    public function forceDelete(User $user, Board $board, Notice $notice)
    {
        return false;
    }
}
