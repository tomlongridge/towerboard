<?php

namespace App\Policies;

use App\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use App\BoardRole;
use App\Board;

class BoardRolePolicy
{
    use HandlesAuthorization;

    /**
     * Determine whether the user can create roles.
     *
     * @param  \App\User  $user
     * @return mixed
     */
    public function create(User $user, Board $board)
    {
        return $board->isAdmin($user);
    }

    /**
     * Determine whether the user can update roles.
     *
     * @param  \App\User  $user
     * @param  \App\Board $board
     * @return mixed
     */
    public function update(User $user, Board $board, BoardRole $role)
    {
        return $board->isAdmin($user) || ($user != null && $user->id == auth()->id());
    }

    /**
     * Determine whether the user can delete roles.
     *
     * @param  \App\User  $user
     * @param  \App\Board $board
     * @return mixed
     */
    public function delete(User $user, Board $board)
    {
        return $board->isAdmin($user) || ($user != null && $user->id == auth()->id());
    }
}
