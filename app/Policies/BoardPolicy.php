<?php

namespace App\Policies;

use App\User;
use App\Board;
use Illuminate\Auth\Access\HandlesAuthorization;

class BoardPolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can view the board.
     *
     * @param  \App\User  $user
     * @param  \App\Board  $board
     * @return mixed
     */
    public function viewAny(?User $user)
    {
        return true;
    }

    /**
     * Determine whether the user can view the board.
     *
     * @param  \App\User  $user
     * @param  \App\Board  $board
     * @return mixed
     */
    public function view(?User $user, Board $board)
    {
        return $board->isApproved() || ($user != null && $board->created_by == $user->id);
    }

    /**
     * Determine whether the user can create boards.
     *
     * @param  \App\User  $user
     * @return mixed
     */
    public function create(?User $user)
    {
        return $user != null && $user->hasVerifiedEmail();
    }

    /**
     * Determine whether the user can update the board.
     *
     * @param  \App\User  $user
     * @param  \App\Board  $board
     * @return mixed
     */
    public function update(User $user, Board $board)
    {
        return $board->isAdmin($user);
    }

    public function subscribeUsers(User $user, Board $board)
    {
        return $board->isAdmin($user) && $board->isApproved();
    }

    /**
     * Determine whether the user can delete the board.
     *
     * @param  \App\User  $user
     * @param  \App\Board  $board
     * @return mixed
     */
    public function delete(User $user, Board $board)
    {
        return $board->isAdmin($user);
    }

    /**
     * Determine whether the user can restore the board.
     *
     * @param  \App\User  $user
     * @param  \App\Board  $board
     * @return mixed
     */
    public function restore(User $user, Board $board)
    {
        return $board->isAdmin($user);
    }

    /**
     * Determine whether the user can permanently delete the board.
     *
     * @param  \App\User  $user
     * @param  \App\Board  $board
     * @return mixed
     */
    public function forceDelete(User $user, Board $board)
    {
        return false;
    }
}
