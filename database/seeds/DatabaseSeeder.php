<?php

use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     *
     * @return void
     */
    public function run()
    {
        $this->call(UsersTableSeeder::class);
        $this->call(TowersTableSeeder::class);
        $this->call(BoardsTableSeeder::class);
        $this->call(SubscriptionTableSeeder::class);
        $this->call(BoardRoleTableSeeder::class);
        $this->call(NoticesTableSeeder::class);
    }
}
